
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    url_timbre_odontologico = fields.Char("URL Timbre Od.")
    usuario_timbre_odontologico = fields.Char("Usuario Timbre Od.")