# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, exceptions, _
from dateutil import rrule
from datetime import datetime, timedelta
import time


class StockMasterPlanning(models.Model):

    _name = "stock.master.planning"

    @api.model
    def _get_default_warehouse(self):
        company_id = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].\
            search([('company_id', '=', company_id)])
        if not warehouse_ids:
            return False
        return warehouse_ids[0]

    name = fields.Char("Description", required=True)
    last_compute_date = fields.Datetime("Last compute date", readonly=True)
    start_date = fields.Date("Start date", required=True,
                             default=lambda self:
                             fields.Date.context_today(self))
    period_type = fields.Selection([('week', "Week"), ('month', 'Month')],
                                   "Period type", required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    period_count = fields.Integer("Period count", required=True, default=1)
    product_ids = fields.Many2many(comodel_name='product.product',
                                   relation='stock_planning_product_rel',
                                   column1='wiz_id', column2='product_id',
                                   string='Products', domain=[("sale_ok", "=",
                                                               True)],
                                   required=True)
    warehouse_id = fields.Many2one("stock.warehouse", "Warehouse",
                                   required=True,
                                   default=_get_default_warehouse)
    demand_ids = fields.One2many("stock.demand", "planning_id", "Demands")
    period_ids = fields.One2many("stock.planning.period", "planning_id",
                                 "Periods", readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed')], "State",
                             readonly=True, default="draft")
    detail_ids = fields.One2many("stock.planning.detail", "planning_id",
                                 "Planning", readonly=True)

    @api.multi
    def action_compute_periods(self):
        plan_period_obj = self.env["stock.planning.period"]
        for plan in self:
            plan.state = "confirmed"
            start_date = datetime.strptime(plan.start_date, "%Y-%m-%d")
            if plan.period_type == "week":
                days = list(rrule.rrule(rrule.WEEKLY,
                                        dtstart=start_date,
                                        count=plan.period_count,
                                        byweekday=rrule.MO))
            else:
                days = list(rrule.rrule(rrule.MONTHLY,
                                        dtstart=start_date,
                                        count=plan.period_count,
                                        bymonthday=-1))
            last_date = days[-1]
            to_unlink_ids = plan_period_obj.\
                search([('end_date', '>', last_date.strftime("%Y-%m-%d")),
                        ('planning_id', '=', plan.id)])
            if to_unlink_ids:
                to_unlink_ids.unlink()
            for period in days:
                domain = [('planning_id', '=', plan.id)]
                if plan.period_type == "week":
                    # Date of sunday
                    end_date = period + timedelta(6)
                    start_date = period
                else:
                    end_date = period
                    start_date = datetime(end_date.year, end_date.month, 1)
                domain.append(('end_date', '=', end_date.strftime("%Y-%m-%d")))
                period_ids = plan_period_obj.search(domain)
                if not period_ids:
                    name = str(start_date.day) + "/" + str(start_date.month)
                    name += " - " + str(end_date.day) + "/" + \
                        str(end_date.month) + " " + str(end_date.year)
                    plan_period_obj.create({"name": name,
                                            "planning_id": plan.id,
                                            "start_date":
                                            start_date.strftime("%Y-%m-%d"),
                                            "end_date":
                                            end_date.strftime("%Y-%m-%d")})
        return True

    @api.multi
    def action_plan(self):
        detail_obj = self.env["stock.planning.detail"]
        demand_obj = self.env["stock.demand"]
        period_obj = self.env["stock.planning.period"]
        for plan in self:
            plan.last_compute_date = time.strftime("%Y-%m-%d %H:%M:%S")
            if not plan.demand_ids or not plan.period_ids:
                raise exceptions.Warning(_("Please, set periods and "
                                           "demands before plan"))

            indirect_products = [x.id for x in plan.product_ids]
            plan.detail_ids.unlink()
            for demand in plan.demand_ids:
                if demand.demand_type == "indirect":
                    demand.unlink()
            plan.refresh()
            for product in plan.product_ids:
                for period in plan.period_ids:
                    detail_obj.create({"planning_id": plan.id,
                                       "product_id": product.id,
                                       "period_id": period.id})

            plan.refresh()
            for detail in plan.detail_ids:
                if detail.needed_qty > 0 and detail.product_id in \
                        plan.product_ids and detail.product_id.bom_ids:
                    for bom_line in detail.product_id.bom_ids[0].bom_line_ids:
                        if bom_line.product_id.id not in indirect_products:
                            indirect_products.append(bom_line.product_id.id)
                            for period in plan.period_ids:
                                detail_obj.create({"planning_id": plan.id,
                                                   "product_id":
                                                   bom_line.product_id.id,
                                                   "period_id": period.id})
                        if bom_line.product_id.seller_delay:
                            ex_date = datetime.\
                                strptime(detail.period_id.end_date,
                                         "%Y-%m-%d") - \
                                timedelta(bom_line.product_id.seller_delay)
                            if ex_date >= datetime.\
                                    strptime(detail.period_id.start_date,
                                             ("%Y-%m-%d")):
                                demand_period = detail.period_id.id
                            else:
                                period_ids = period_obj.\
                                    search([('start_date', '<=', ex_date),
                                            ('end_date', '>=', ex_date),
                                            ('planning_id', '=', plan.id)])
                                if not period_ids:
                                    raise exceptions.\
                                        Warning(_("Cannot plan with these "
                                                  "periods because %s need a "
                                                  "period for %s")
                                                % (bom_line.product_id.name,
                                                   ex_date))
                                else:
                                    demand_period = period_ids[0].id
                        demand_obj.create({'product_id':
                                           bom_line.product_id.id,
                                           'planning_id': plan.id,
                                           'period_id': demand_period,
                                           'demand_type': 'indirect',
                                           'product_qty': detail.needed_qty *
                                           bom_line.product_qty})
        return True
