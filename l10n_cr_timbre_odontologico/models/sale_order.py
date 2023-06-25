

from odoo import models, fields, api, _
from odoo.exceptions import UserError



class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_timbre = fields.Boolean("Es timbre",compute="_compute_is_timbre")
    
    @api.depends("order_line","order_line.product_id")
    def _compute_is_timbre(self):
        for record in self:
            line_timbre = self.order_line.filtered(lambda l:l.product_id.exent_product)
            if line_timbre:
                record.is_timbre = True
            else:
                record.is_timbre = False

    @api.onchange('order_line')
    def _onchange_order_line(self):        
        for record in self:
            if record.is_timbre:
                line_id = record.order_line.filtered(lambda l:l.product_id.id == self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id)
                if line_id:
                    record.order_line = [(2,line_id[0].id,0)]
                priceu = sum(record.order_line.filtered(lambda l:l.product_id.id != self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id and l.product_id.exent_product).mapped("price_subtotal")) *.05    
                record.order_line = [(0,0,{
                    "product_id": self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id,
                    "name": self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").name,
                    "price_unit": priceu,
                    "product_uom_qty": 1,
                    "product_uom":self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").uom_id.id,
                    "price_subtotal": priceu,
                })]
                # record.order_line[-1]._onchange_price_subtotal()
                
            else:
                line_id = record.order_line.filtered(lambda l:l.product_id.id == self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id)
                if line_id:
                    record.order_line = [(2,line_id[0].id,0)]