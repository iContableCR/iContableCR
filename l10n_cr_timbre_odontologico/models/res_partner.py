
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_partner_to_timbre = fields.Boolean("Es Timbre",default=False)