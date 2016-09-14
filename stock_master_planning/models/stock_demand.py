# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields
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
    product_qty = fields.Float("Qty.", digits_compute=
                               dp.get_precision('Product Unit of Measure'))
    demand_type = fields.Selection([('direct', 'Direct'),
                                    ('indirect', 'Indirect')], "Type",
                                   required=True, readonly=True,
                                   default="direct")
