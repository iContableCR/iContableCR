
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    correo_timbre_odontologico = fields.Many2one("res.partner","Correo",domain="[('is_partner_to_timbre','=',True)]")