# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, _, exceptions, api
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare, float_round
import time
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class StockDemandEstimate(models.Model):
    _inherit = 'stock.demand.estimate'
    _order = "end_date asc"

    def get_previous_demand(self, demand):
        prev_ids = self.search(
            [('end_date', '>=', time.strftime("%Y-%m-%d")),
             ('end_date', '<=', demand.period_id.date_from),
             ('location_id', '=', demand.location_id.id),
             ('product_id', '=', demand.product_id.id),
             ('demand_type', '=', 'stock'),
             ('id', '<>', demand.id)]).sorted()
        if prev_ids:
            return prev_ids[-1]
        else:
            False

    @api.multi
    #@api.depends('product_uom_qty', 'indirect_demand_qty', 'action_needed',
    #             'procurement_id', 'procurement_id.state')
    def calculate_needs(self):

        _logger.info('calculate_needs')
        demands = self.filtered(
                    lambda x: x.demand_type not in ['buy',
                                                    'manufacture']).sorted()\
                  + self.filtered(
            lambda x: x.demand_type in ['buy','manufacture']).sorted()
        for demand in demands:
            _logger.info('Calculating values in period %s type %s for %s',
                         demand.period_id.name, demand.demand_type,
                         demand.product_id.name)
            if demand.demand_type == 'stock':
                prod = self.env['product.product'].with_context(
                    {'location': demand.location_id.id,
                     'from_date': demand.period_id.date_from,
                     'to_date': demand.period_id.date_to}). \
                    browse(demand.product_id.id)

                # incoming qty in planning period
                demand.incoming_qty = prod.incoming_qty
                # outgoing qty in planning period
                demand.outgoing_qty = prod.outgoing_qty

                prod2 = self.env['product.product'].with_context(
                    {'location': demand.location_id.id,
                     'to_date': demand.period_id.date_to}). \
                    browse(demand.product_id.id)

                date_ini = fields.Date.to_string(
                    fields.Date.from_string(demand.period_id.date_from) -
                    relativedelta(days=1))

                prod_ini = self.env['product.product'].with_context(
                    {'location': demand.location_id.id,
                     'to_date': date_ini}). \
                    browse(demand.product_id.id)

                prev_demand_ids = self.search(
                    [('end_date', '>=', time.strftime("%Y-%m-%d")),
                     ('end_date', '<=', demand.period_id.date_from),
                     ('location_id', '=', demand.location_id.id),
                     ('product_id', '=', demand.product_id.id),
                     ('demand_type', '=', 'stock'),
                     ('id', '<>', demand.id)])

                # STOCK INICIAL EN CADA PERÍODO
                if demand.period_id.date_from <= time.strftime("%Y-%m-%d"):
                    # para el períod inicial es el sotock vitual
                    demand.initial_stock_qty = prod_ini.virtual_available
                else:
                    # se calcual par alos demás sumando el su stock final
                    # previsto = inicial - demanda calculada + stock necesario
                    prev_demand = self.get_previous_demand(demand)
                    if prev_demand:
                        demand.initial_stock_qty = prev_demand.final_stock_qty
                    else:
                        demand.initial_stock_qty = prod_ini.virtual_available


                # TODO Revisar si hacerlo así o por el mayor entre indirecta +
                # salida y la previsión de demanda
                demand.demand_qty = max(demand.product_uom_qty,
                                        (demand.indirect_demand_qty +
                                         demand.outgoing_qty))

                demand.expected_qty = demand.initial_stock_qty - \
                                      demand.demand_qty + demand.incoming_qty

                demand.needed_qty = 0
                orderpoint_ids = self.env["stock.warehouse.orderpoint"]. \
                    search([('product_id', '=', demand.product_id.id),
                            ('location_id', '=', demand.location_id.id)])

                if orderpoint_ids:
                    op = orderpoint_ids[0]
                    if float_compare(demand.expected_qty, op.product_min_qty,
                                     precision_rounding=op.product_uom.rounding) \
                            < 0:
                        qty = max(op.product_min_qty, op.product_max_qty) - \
                              demand.expected_qty
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
                            demand.needed_qty = qty_rounded

                elif demand.expected_qty < 0:
                    demand.needed_qty = abs(demand.expected_qty)
                demand.final_stock_qty = demand.expected_qty + \
                                         demand.needed_qty

            else:   # Buy and Manufacture
                demand.expected_qty = 0
                demand.needed_qty = demand.indirect_demand_qty

            if demand.action_needed and demand.needed_qty > 0 and not \
                    demand.procurement_id:
                demand.action_needed_compute = True
            else:
                demand.action_needed_compute = False


    demand_type = fields.Selection([('stock', 'Stock'),
                                    ('buy', 'Buy'),
                                    ('manufacture', 'Manufacture')], "Type",
                                   required=True, readonly=True,
                                   default="stock")
    end_date = fields.Date('End date', related='period_id.date_to',
                           readonly=True, store=True)
    category_id = fields.Many2one('product.category', 'Category',
                                  related='product_id.categ_id', store=True,
                                  readonly=True)
    qty_available = fields.Float('Real stock', readonly=True,
                                 digits_compute=
                                 dp.get_precision('Product Unit of Measure'))
    incoming_qty = fields.Float('Incoming', readonly=True,
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    outgoing_qty = fields.Float('Outgoing', readonly=True,
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    initial_stock_qty = fields.Float("Initial Stock", readonly=True,
                              help='Initial stock in period')
    final_stock_qty = fields.Float("Final stock", readonly=True,
                                     help = 'Final stock in period')
    demand_qty = fields.Float("Demand", readonly=True,
                              digits_compute=
                              dp.get_precision('Product Unit of Measure'))
    indirect_demand_qty = fields.Float("Indirect Demand", readonly=True,
                                       multi=True)
    net_demand_qty = fields.Float("Net Demand", readonly=True,
                                  digits_compute=
                                  dp.get_precision('Product Unit of '
                                                   'Measure'))
    expected_qty = fields.Float("Expected qty.", readonly=True,
                                digits_compute=
                                dp.get_precision('Product Unit of Measure'))
    needed_qty = fields.Float("Needed qty.", readonly=False,
                              digits_compute=
                              dp.get_precision('Product Unit of Measure'))
    generated_by_id = fields.Many2one('stock.demand.estimate', 'Generated by',
                                      readonly=True)
    generated_by_ids = fields.Many2many(comodel_name='stock.demand.estimate',
                                       relation='stock_demand_rel',
                                       column1='parent_id', column2='child',
                                       string='Generated by', readonly=True)
    rule_id = fields.Many2one('procurement.rule', 'Origin rule',
                                      readonly=True)
    action_needed = fields.Boolean('Action Neded')
    action_needed_compute = fields.Boolean('Action Neded', )
    procurement_id =  fields.Many2one('procurement.order', 'Procurement',
                                      readonly=True)
    executed = fields.Boolean('Action executed', default=False)



    @api.multi
    def create_bom_demands(self, needed_qty, rule_id):
        demand = self.env['stock.demand.estimate']
        uom_obj = self.env['product.uom']
        bom_obj = self.env['mrp.bom']
        product_obj = self.env['product.product']
        bom_points = self.product_id.bom_ids
        if not bom_points:
            raise exceptions. \
                Warning(_("Configuration Error: "
                          "Product '%s' needs a "
                          "bill of material")
                        % (self.product_id.name))
        else:
            bom_point = bom_points[0]
        manufacture_obj = self.env['mrp.production']
        defaults = manufacture_obj.default_get(['location_src_id'])
        location_mp_id = defaults['location_src_id']
        if bom_point:
            demand += self.generate_manufacture_demand(needed_qty, rule_id)
        else:
            raise exceptions. \
                Warning(_("Configuration Error: "
                          "Product '%s' needs a "
                          "bill of material")
                        % (self.product_id.name))
        factor = uom_obj._compute_qty(self.product_uom and
                                      self.product_uom.id or
        self.product_id.uom_id.id, needed_qty,
                                      bom_point.product_uom.id)
        # product_lines, workcenter_lines
        res1, res2 = bom_obj._bom_explode(bom_point, self.product_id,
                                          factor / bom_point.product_qty)

        for bom_line in res1:
            demand_period = self.period_id.id
            product = product_obj.browse(bom_line['product_id'])[0]
            # if product.seller_delay:
            #     ex_date = datetime.strptime(self.period_id.date_to,
            #                                 "%Y-%m-%d") - \
            #         timedelta(product.seller_delay)
            #     if ex_date >= datetime.strptime(
            #             self.period_id.date_from, ("%Y-%m-%d")):
            #         demand_period = self.period_id.id
            #     else:
            #         period_ids = self.env['stock.demand.estimate.period'].\
            #             search([('date_from', '<=', ex_date),
            #                     ('date_to', '>=', ex_date),
            #                     ])
            #         if not period_ids:
            #             raise exceptions.\
            #                 Warning(_("Cannot plan with these "
            #                           "periods because %s need a "
            #                           "period for %s")
            #                         % (product.name,
            #                            ex_date))
            #         else:
            #             demand_period = period_ids[0].id

            exist_demand = self.env['stock.demand.estimate'].search(
                [('location_id', '=', location_mp_id),
                 ('period_id', '=', demand_period),
                 ('product_id', '=', bom_line['product_id']),
                 ('demand_type', '=', self.demand_type)
                 ])
            if exist_demand:
                exist_demand.indirect_demand_qty += bom_line['product_qty']
                exist_demand.write({'generated_by_ids': [(4, self.id)]})
                demand += exist_demand
            else:
                demand += self.create(
                    {'product_id': bom_line['product_id'],
                     'product_uom': product.uom_id.id,
                     'location_id': location_mp_id,
                     'period_id': demand_period,
                     #'demand_type': 'indirect',
                     'indirect_demand_qty': bom_line['product_qty'],
                     'generated_by_ids': [(4, self.id)],
                     'action_needed': True })
        return demand

    @api.multi
    def explode_route(self, needed_qty):
        demand = self.env['stock.demand.estimate']
        rules = self.env['procurement.rule'].search(
            [('location_id', '=', self.location_id.id),
             ('action', '=', 'move')])
        if rules:
            if len(rules) != 1:
                raise exceptions.Warning(_("Error rules for location %s. "
                                           "%s move rule found")
                                         % (self.location_id.name, len(rules)))
            exist_demand = self.search(
                [('location_id', '=', rules.location_src_id.id),
                 ('period_id', '=', self.period_id.id),
                 ('product_id', '=', self.product_id.id),
                 ('demand_type', '=', 'stock')
                 ])
            if exist_demand:
                exist_demand.indirect_demand_qty += needed_qty
                exist_demand.write({'generated_by_ids': [(4, self.id)]})
                demand = exist_demand

            else:
                demand_period = self.period_id.id
                if rules.delay:
                    demand_period = self.get_period(rules.delay)
                if rules.location_src_id.usage == 'internal':
                    action_needed = True
                else:
                    action_needed = False
                demand += self.copy(
                    {'product_uom_qty':0,
                     'location_id': rules.location_src_id.id,
                     'period_id': demand_period,
                     'rule_id': rules.id,
                     'indirect_demand_qty': needed_qty,
                     'generated_by_ids': [(4, self.id)],
                     'action_needed': action_needed
                     }
                    )

        else:
            """Se busca la ruta del producto"""
            route_pulls = self.product_id.route_ids[0].pull_ids
            pulls = route_pulls.filtered(
                lambda r: r.action != 'move' and r.location_id.id == self.location_id.id)

            for pull in pulls:
                if pull.action == 'buy':
                    demand += self.generate_buy_demand(needed_qty, pull.id)
                    break
                if pull.action == 'manufacture':
                    demand += self.create_bom_demands(needed_qty, pull.id)
                    break
        demand.calculate_needs()
        return demand

    @api.multi
    def get_period(self, delay):
        ex_date = datetime.strptime(self.period_id.date_from,
                                    "%Y-%m-%d") - timedelta(delay)
        if ex_date >= datetime.strptime(
                self.period_id.date_from, ("%Y-%m-%d")):
            demand_period = self.period_id.id
        else:
            period_ids = self.env['stock.demand.estimate.period']. \
                search([('date_from', '<=', ex_date),
                        ('date_to', '>=', ex_date),
                        ])
            if not period_ids:
                raise exceptions. \
                    Warning(_("Cannot plan with these "
                              "periods because %s need a "
                              "period for %s")
                            % (self.product_id.name,
                               ex_date))
            else:
                demand_period = period_ids[0].id
        return demand_period

    @api.multi
    def generate_buy_demand(self, needed_qty, rule_id):
        self.action_needed = False
        if self.product_id.seller_delay:
            demand_period = self.get_period(self.product_id.seller_delay)
        else:
            demand_period = self.period_id.id
        exist_buy = self.search(
            [('period_id', '=', demand_period), ('demand_type', '=', 'buy'),
             ('product_id', '=', self.product_id.id)])
        if exist_buy:
            if exist_buy.indirect_demand_qty != needed_qty:
                exist_buy.indirect_demand_qty = needed_qty
                exist_buy.write({'generated_by_ids': [(4, self.id)]})
            demand = exist_buy
        else:

            demand = self.copy(
                {'product_uom_qty': 0,
                 'demand_type': 'buy',
                 'period_id': demand_period,
                 'indirect_demand_qty': needed_qty,
                 #'generated_by_id': self.id,
                 'generated_by_ids': [(4, self.id)],
                 'rule_id': rule_id,
                 'action_needed': True
                 })
        return demand

    @api.multi
    def generate_manufacture_demand(self, needed_qty, rule_id):
        self.action_needed = False
        if self.product_id.produce_delay:
            demand_period = self.get_period(self.product_id.produce_delay)
        else:
            demand_period = self.period_id.id
        exist_manufacture = self.search(
            [('period_id', '=', demand_period), ('demand_type', '=',
                                                 'manufacture'),
             ('product_id', '=', self.product_id.id)])
        if exist_manufacture:
            if exist_manufacture.indirect_demand_qty != needed_qty:
                exist_manufacture.indirect_demand_qty = needed_qty
                exist_manufacture.write({'generated_by_ids': [(4, self.id)]})
            demand = exist_manufacture
        else:

            demand = self.copy(
                {
                    'demand_type': 'manufacture',
                    #'generated_by_id': self.id,
                    'period_id': demand_period,
                    'indirect_demand_qty': needed_qty,
                    'generated_by_ids': [(4, self.id)],
                    'rule_id': rule_id,
                    'action_needed': True
                })
        return demand