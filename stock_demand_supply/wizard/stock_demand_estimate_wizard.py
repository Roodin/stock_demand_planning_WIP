# -*- coding: utf-8 -*-
# © 2016 Comunitea Servicios Tecnológicos S.L..
#   (http://comunitea.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError


class StockDemandEstimateSheet(models.TransientModel):
    _inherit = 'stock.demand.estimate.sheet'


    def _prepare_estimate_data(self, line):
        data = super(StockDemandEstimateSheet, self)._prepare_estimate_data(
            line)
        data['action_needed'] = True
        return data