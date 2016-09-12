# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api
from dateutil import rrule
from datetime import datetime, timedelta


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
                                   "Period type", required=True,
                                   states={'confirmed': [('readonly', True)]})
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

    @api.multi
    def action_create_periods(self):
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

