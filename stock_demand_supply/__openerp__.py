# -*- coding: utf-8 -*-
##############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Stock Demand Supply Chain',
    "version": "8.0.2.0.0",
    "author": "Comunitea",
    'website': "http://www.comunitea.com",
    'category': 'Warehouse Management',
    "license": 'AGPL-3',
    "contributors": [
        "Omar Castiñeira Saavedra <omar@comunitea.com>",
        "Jesús Ventosinos <jesus@comunitea.com>",
        "Santi Argüeso <santi@comunitea.com>",
        
    ],
    'depends': ['stock_demand_estimate'],
    'data': ['wizard/procurement_request.xml',
             'wizard/stock_planning_wizard_view.xml',
             'views/stock_demand_estimate_view.xml',
            ],
    'installable': True,
}
