# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare, float_round
import time


class StockPlanningDetail(models.Model):

    _name = "stock.planning.detail"

    @api.one
    def _get_product_info_location(self):
        demand_obj = self.env["stock.demand"]
        prod = self.env['product.product'].with_context(
            {'warehouse': self.planning_id.warehouse_id.id,
             'from_date': self.period_id.start_date,
             'to_date': self.period_id.end_date}).\
            browse(self.product_id.id)
        self.qty_available = prod.qty_available
        # incoming qty in planning period
        self.incoming_qty = prod.incoming_qty
        # outgoing qty in planning period
        self.outgoing_qty = prod.outgoing_qty
        demand_ids = demand_obj.search([('product_id', '=',
                                         self.product_id.id),
                                        ('period_id', '=', self.period_id.id)])
        demand_qty = 0
        for demand in demand_ids:
            demand_qty += demand.product_qty
        # sum of products demands in planning period
        self.demand_qty = demand_qty

        prod2 = self.env['product.product'].with_context(
            {'warehouse': self.planning_id.warehouse_id.id,
             'to_date': self.period_id.end_date}).\
            browse(self.product_id.id)

        # net demand
        if self.period_id.end_date < time.strftime("%Y-%m-%d"):
            self.net_demand_qty = 0
        else:
            self.net_demand_qty = (demand_qty - prod.outgoing_qty)

        # available stock in planning period
        if self.net_demand_qty > 0:
            expected_qty = prod2.virtual_available - self.net_demand_qty
        else:
            expected_qty = prod2.virtual_available

        detail_ids = self.search([('end_date', '>=',
                                   time.strftime("%Y-%m-%d")),
                                  ('end_date', '<=',
                                   self.period_id.start_date),
                                  ('planning_id', '=',
                                   self.planning_id.id),
                                  ('product_id', '=', self.product_id.id)])
        for detail in detail_ids:
            expected_qty -= detail.net_demand_qty
            expected_qty += detail.needed_qty
        self.expected_qty = expected_qty

        self.needed_qty = 0
        orderpoint_ids = self.env["stock.warehouse.orderpoint"].\
            search([('product_id', '=', self.product_id.id),
                    ('warehouse_id', '=', self.planning_id.warehouse_id.id)])
        if orderpoint_ids:
            op = orderpoint_ids[0]
            if float_compare(self.expected_qty, op.product_min_qty,
                             precision_rounding=op.product_uom.rounding) \
                    < 0:
                qty = max(op.product_min_qty, op.product_max_qty) - \
                    self.expected_qty
                reste = op.qty_multiple > 0 and qty % op.qty_multiple or \
                    0.0
                if float_compare(reste, 0.0,
                                 precision_rounding=
                                 op.product_uom.rounding) > 0:
                    qty += op.qty_multiple - reste

                qty_rounded = float_round(qty,
                                          precision_rounding=
                                          op.product_uom.rounding)
                if qty_rounded > 0:
                    self.needed_qty = qty_rounded
        elif self.expected_qty < 0:
            self.needed_qty = abs(self.expected_qty)

    planning_id = fields.Many2one("stock.master.planning", "Planning",
                                  readonly=True, required=True,
                                  ondelete="cascade")
    product_id = fields.Many2one("product.product", "Product", required=True)
    period_id = fields.Many2one("stock.planning.period", "Period",
                                required=True)
    end_date = fields.Date("End date", related="period_id.end_date",
                           readonly=True)
    category_id = fields.Many2one('product.category', 'Category',
                                  related='product_id.categ_id', store=True,
                                  readonly=True)
    qty_available = fields.Float('Real stock', readonly=True, multi=True,
                                 compute='_get_product_info_location',
                                 digits_compute=
                                 dp.get_precision('Product Unit of Measure'))
    incoming_qty = fields.Float('Incoming', readonly=True, multi=True,
                                compute='_get_product_info_location',
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    outgoing_qty = fields.Float('Outgoing', readonly=True, multi=True,
                                compute='_get_product_info_location',
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    demand_qty = fields.Float("Demand", readonly=True, multi=True,
                              compute='_get_product_info_location',
                              digits_compute=
                              dp.get_precision('Product Unit of Measure'))
    net_demand_qty = fields.Float("Net Demand", readonly=True, multi=True,
                                  compute='_get_product_info_location',
                                  digits_compute=
                                  dp.get_precision('Product Unit of Measure'))
    expected_qty = fields.Float("Expected qty.", readonly=True, multi=True,
                                compute='_get_product_info_location',
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    needed_qty = fields.Float("Needed qty.", readonly=True, multi=True,
                              compute='_get_product_info_location',
                              digits_compute=
                              dp.get_precision('Product Unit of Measure'))
