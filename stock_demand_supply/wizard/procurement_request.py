# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################


import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api
import time


class WizStockProcurementRequest(models.TransientModel):
    _name = "stock.procurement.request"
    _description = "Procurement request"

    product_id = fields.Many2one('product.product',
            string='Product',
            required=True)
    product_qty = fields.Float('Quantity', 
            digits_compute=dp.get_precision('Product Unit of Measure'),
            required=True)
    period_id = fields.Many2one('stock.demand.estimate.period',
            string='Period', required=True)
    stock_demand_id = fields.Many2one('stock.demand.estimate',
            string='Period', required=True)
    action_date = fields.Date("Action date (Buy or Produce)", readonly=True)
    procurement_date = fields.Date("Procurement date")

    @api.model
    def default_get(self, list_fields):
        res = super(WizStockProcurementRequest, self).default_get(list_fields)
        stock_demand_obj = self.env['stock.demand.estimate']
        demand = stock_demand_obj.browse(self.env.context.get('active_id'))
        
        if 'product_id' in list_fields:
            res.update({'product_id': demand.product_id.id})
        if 'product_qty' in list_fields:
            res.update({'product_qty': demand.needed_qty})
        if 'period_id' in list_fields:
           res.update({'period_id': demand.period_id.id})
        if 'stock_demand_id' in list_fields:
           res.update({'stock_demand_id': demand.id})

        if 'action_date' in list_fields:
            res.update({'action_date': demand.period_id.date_from})
        if 'procurement_date' in list_fields:
            if demand.demand_type == 'manufacture':
                date = fields.Date.to_string(
                    fields.Date.from_string(demand.period_id.date_from) +
                    relativedelta(days=demand.product_id.produce_delay))

            elif demand.demand_type == 'buy':
                date = fields.Date.to_string(
                    fields.Date.from_string(demand.period_id.date_from) +
                    relativedelta(days=demand.product_id.seller_delay))
            else:
                date = demand.period_id.date_from

            res.update({'procurement_date': date})
        return res

    @api.multi
    def generate_procurement(self):
        vals = self._prepare_procurement_vals()
        vals_group = self._prepare_procurement_group_vals()
        procurement_group_obj = self.env['procurement.group']
        procurement_obj = self.env['procurement.order']
        proc_group = procurement_group_obj.create(vals_group)
        vals['group_id'] = proc_group.id
        print vals
        proc = procurement_obj.create(vals)
        proc.run()
        self.stock_demand_id.write({'procurement_id': proc.id, 'executed':
                                    True})
        demand_obj = self.env["stock.demand.estimate"]
        demand_ids = demand_obj.search([('end_date', '>=',
                                         self.procurement_date)])
        demand_ids.refresh()

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _prepare_procurement_vals(self):
        warehouses = self.env['stock.warehouse'].search([])
        proc_wh_id = False
        for warehouse in warehouses:
            loc_warehouse_ids = self.env['stock.location'].search(
                [('id', 'child_of',warehouse.lot_stock_id.id)])
            if self.stock_demand_id.location_id.id in\
                    [x.id for x in loc_warehouse_ids]:
                proc_wh_id = warehouse.id
                break
            else:
                proc_wh_id = warehouses[0].id
        print proc_wh_id
        #stock_demand_obj = self.env['stock.demand.estimate']
        demand = self.stock_demand_id
        if demand.demand_type in ['buy', 'manufacture'] and \
                demand.generated_by_id:
            period = demand.generated_by_id.period_id
        else:
            period = self.period_id
        return {
            'name': 'MPS/'+ self.period_id.name,
            'origin': 'MPS/'+ self.period_id.name,
            'date_planned': self.procurement_date,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom': self.product_id.uom_id.id,
            'product_uos_qty': self.product_qty,
            'product_uos': self.product_id.uom_id.id,
            'company_id': self.stock_demand_id.company_id.id,
            'warehouse_id': proc_wh_id,
            'location_id': self.stock_demand_id.location_id.id,
        }

    @api.multi
    def _prepare_procurement_group_vals(self):
        return {
            'name': 'MPS/' + self.period_id.name
        }

        
