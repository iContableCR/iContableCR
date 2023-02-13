
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    exent_product = fields.Boolean("Excento",default=False, related="product_tmpl_id.exent_product")
