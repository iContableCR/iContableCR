from odoo import models, fields


class PaymentMethods(models.Model):
    _name = "payment.methods"
    _description = "Payment Methods for Electronic Invoice"

    # ==============================================================================================
    #                                          PAYMENT METHODS
    # ==============================================================================================

    active = fields.Boolean(
        default=True
    )
    sequence = fields.Char()
    name = fields.Char()
    notes = fields.Text()
