# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, _, exceptions, api
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp


class StockDemand(models.Model):

    _name = "stock.demand"

    product_id = fields.Many2one("product.product", "Product", required=True,
                                 domain=[('type', '!=', 'service')])
    planning_id = fields.Many2one("stock.master.planning", "Planning",
                                  readonly=True, required=True,
                                  ondelete="cascade")
    period_id = fields.Many2one("stock.planning.period", "Period",
                                required=True, ondelete="cascade")
    product_qty = fields.Float(
        "Qty.", digits_compute=dp.get_precision('Product Unit of Measure'))
    demand_type = fields.Selection([('direct', 'Direct'),
                                    ('indirect', 'Indirect')], "Type",
                                   required=True, readonly=True,
                                   default="direct")
    location_id = fields.Many2one('stock.location', 'Location',
                                  domain=[('usage', 'in',
                                          ('internal', 'customer'))],
                                  required=True)

    @api.multi
    def create_detail(self):
        self.ensure_one()

        return self.env['stock.planning.detail'].create(
            {'planning_id': self.planning_id.id,
             'product_id': self.product_id.id,
             'period_id': self.period_id.id,
             'location_id': self.location_id.id,
             'demand_id': self.id})

    @api.multi
    def create_bom_demands(self, needed_qty):
        demand = self.env['stock.demand']
        for bom_line in self.product_id.bom_ids[0].bom_line_ids:
            demand_period = self.period_id.id
            if bom_line.product_id.seller_delay:
                ex_date = datetime.strptime(self.period_id.end_date,
                                            "%Y-%m-%d") - \
                    timedelta(bom_line.product_id.seller_delay)
                if ex_date >= datetime.strptime(
                        self.period_id.start_date, ("%Y-%m-%d")):
                    demand_period = self.period_id.id
                else:
                    period_ids = self.env['stock.planning.period'].\
                        search([('start_date', '<=', ex_date),
                                ('end_date', '>=', ex_date),
                                ('planning_id', '=',
                                 self.planning_id.id)])
                    if not period_ids:
                        raise exceptions.\
                            Warning(_("Cannot plan with these "
                                      "periods because %s need a "
                                      "period for %s")
                                    % (bom_line.product_id.name,
                                       ex_date))
                    else:
                        demand_period = period_ids[0].id

            exist_demand = self.env['stock.demand'].search(
                [('location_id', '=', self.location_id.id),
                 ('period_id', '=', demand_period),
                 ('demand_type', '=', 'indirect'),
                 ('planning_id', '=', self.planning_id.id),
                 ('product_id', '=', bom_line.product_id.id),
                 ])
            if exist_demand:
                exist_demand.product_qty += needed_qty * bom_line.product_qty
            else:
                demand += self.create(
                    {'product_id': bom_line.product_id.id,
                     'planning_id': self.planning_id.id,
                     'location_id': self.location_id.id,
                     'period_id': demand_period,
                     'demand_type': 'indirect',
                     'product_qty': needed_qty * bom_line.product_qty})
        return demand

    @api.multi
    def explode_route(self, needed_qty):
        demand = self.env['stock.demand']
        rules = self.env['procurement.rule'].search(
            [('warehouse_id', '=', self.planning_id.warehouse_id.id),
             ('location_id', '=', self.location_id.id),
             ('action', '=', 'move')])
        if rules:
            if len(rules) != 1:
                raise exceptions.Warning(_('Error rules'), _(''))
            exist_demand = self.env['stock.demand'].search(
                [('location_id', '=', rules.location_src_id.id),
                 ('period_id', '=', self.period_id.id),
                 ('demand_type', '=', 'indirect'),
                 ('planning_id', '=', self.planning_id.id),
                 ('product_id', '=', self.product_id.id),
                 ])
            if exist_demand:
                exist_demand.product_qty += needed_qty
            else:
                demand_period = self.period_id.id
                if rules.delay:
                    ex_date = datetime.strptime(self.period_id.end_date,
                                                "%Y-%m-%d") - \
                        timedelta(rules.delay)
                    if ex_date >= datetime.strptime(
                            self.period_id.start_date, ("%Y-%m-%d")):
                        demand_period = self.period_id.id
                    else:
                        period_ids = self.env['stock.planning.period'].\
                            search([('start_date', '<=', ex_date),
                                    ('end_date', '>=', ex_date),
                                    ('planning_id', '=',
                                     self.planning_id.id)])
                        if not period_ids:
                            raise exceptions.\
                                Warning(_("Cannot plan with these "
                                          "periods because %s need a "
                                          "period for %s")
                                        % (self.product_id.name,
                                           ex_date))
                        else:
                            demand_period = period_ids[0].id
                demand += self.copy(
                    {'location_id': rules.location_src_id.id,
                     'period_id': demand_period,
                     'demand_type': 'indirect',
                     'product_qty': needed_qty})
        else:
            """Se busca la ruta del producto"""
            route_pulls = self.product_id.route_ids[0].pull_ids
            pull = route_pulls.filtered(
                lambda r: r.warehouse_id == self.planning_id.warehouse_id and
                r.action != 'move')
            if not pull:
                raise exceptions.Warning(_('Error rules'), _(''))
            elif pull.action == 'manufacture':
                demand += self.create_bom_demands(needed_qty)
        return demand
