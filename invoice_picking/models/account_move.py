from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    picking_count = fields.Integer("Entregas",compute="compute_stock_picking",copy=False)
    stock_picking_ids = fields.Many2many(comodel_name="stock.picking",string="Transferencias",relation='account_moves_stock_pickings_rel',copy=False)

    @api.depends("stock_picking_ids")
    def compute_stock_picking(self):
        for order in self:
            order.picking_count = len(order.stock_picking_ids)

    def prepare_values_stock_picking(self,picking_type):
        values = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'move_type': 'direct'
        }
        if picking_type.code == 'outgoing':
            values.update({
                'location_dest_id': self.partner_id.property_stock_customer.id,
                'location_id': picking_type.default_location_src_id.id,    
            })
        if picking_type.code == 'incoming':
            values.update({
                'location_dest_id': picking_type.default_location_dest_id.id,
                'location_id': self.partner_id.property_stock_supplier.id,
            })
        return values
    
    def create_stock_picking(self):
        for order in self:
            code = False
            if self.move_type == 'out_invoice':
                code = 'outgoing'
            if self.move_type == 'in_invoice':
                code = 'incoming'
            if self.move_type == 'out_refund':
                code = 'incoming'
            if self.move_type == 'in_refund':
                code = 'outgoing'
            picking_type = self.env['stock.picking.type'].search([('code','=',code)],limit=1)
            if picking_type:
                pickings = self.env['stock.picking'].create(self.prepare_values_stock_picking(picking_type))
                order.stock_picking_ids = [(6,0,pickings.ids)]
                moves = order.invoice_line_ids.filtered(
                    lambda r: r.product_id.type in ['product', 'consu']).create_stock_move(pickings)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
                pickings.button_validate()
    
    def action_post(self):
        res = super(AccountMove,self).action_post()
        if self.move_type in ('out_invoice','in_invoice','out_refund','in_refund'):
            self.create_stock_picking()
        return res
    
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_ready').read()[0]
        action.pop('id', None)
        action.update({
            'context': {},
            'domain': [('id', 'in', self.stock_picking_ids.ids)]
        })
        if self.stock_picking_ids:
            res = self.env.ref('stock.view_picking_form', False)
            action.update({
                'views': [(res and res.id or False, 'form')],
                'res_id': self.stock_picking_ids.id or False
            })
        return action

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list, cancel)
        for moves in reverse_moves:
            if moves.move_type in ('out_invoice','in_invoice','out_refund','in_refund'):
                moves.create_stock_picking()
        return reverse_moves
