
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    xml_timbre = fields.Binary("Archivo Timbre Od.")
    