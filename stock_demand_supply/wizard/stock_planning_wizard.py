# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, exceptions, _
from dateutil import rrule
from datetime import datetime, timedelta
import time


class WizStockMasterPlanning(models.TransientModel):

    _name = "wizard.stock.master.planning"

    @api.multi
    def action_plan(self):
        demand_obj = self.env["stock.demand.estimate"]
        demand_ids = demand_obj.search([('end_date', '>=',
                                         time.strftime("%Y-%m-%d %H:%M:%S"))])
        #indirect_demand_ids = demand_ids.filtered(
        #        lambda d: d.demand_type == 'indirect')
        #indirect_demand_ids.unlink()
        #demands = demand_ids - indirect_demand_ids
        demand_ids.write({'indirect_demand_qty': 0})
        while demand_ids:
            new_demands = self.env['stock.demand.estimate']
            demand = demand_ids[0]
            #new_detail = demand.create_detail()
            demand.refresh()
            if demand.needed_qty > 0 and demand.demand_type == 'stock':
                new_demands = demand.explode_route(demand.needed_qty)
            demand_ids -= demand
            print new_demands
            for new in new_demands:
                if new.demand_type == 'stock':
                    demand_ids += new
        return True
