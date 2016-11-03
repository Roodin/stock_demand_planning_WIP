# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api


class StockPlanningPeriod(models.Model):

    _name = "stock.planning.period"
    _order = "end_date asc"

    name = fields.Char("Name", required=True)
    planning_id = fields.Many2one("stock.master.planning", "Planning",
                                  readonly=True, required=True,
                                  ondelete="cascade")
    start_date = fields.Date("Start date", required=True, readonly=True)
    end_date = fields.Date("End date", required=True, readonly=True)

    @api.multi
    def unlink(self):
        for period in self:
            demand_ids = self.env["stock.demand"].search([('period_id', '=',
                                                           period.id)])
            if demand_ids:
                demand_ids.unlink()
        return super(StockPlanningPeriod, self).unlink()
