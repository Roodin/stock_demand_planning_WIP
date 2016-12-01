# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _make_production_produce_line(self, production):
        res = super(MrpProduction, self).\
            _make_production_produce_line(production)

        production.move_created_ids.write(
            {'date_expected': production.date_planned})