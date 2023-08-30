from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def prepare_values_stock_move(self,line,picking):
        price_unit = line.price_unit
        values = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'company_id': line.move_id.company_id.id,
                    'price_unit': price_unit,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'product_uom_qty': 0,
                    'quantity_done': line.quantity,
                }
        if picking.picking_type_id.code == 'outgoing':
            values.update({
                'location_id': picking.picking_type_id.default_location_src_id.id,
                'location_dest_id': line.move_id.partner_id.property_stock_customer.id,
            })
        if picking.picking_type_id.code == 'incoming':
            values.update({
                'location_id': line.move_id.partner_id.property_stock_supplier.id,
                'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
            })
        return values

    def create_stock_move(self, picking):
        values = []
        for move_line in self:
            template = self.prepare_values_stock_move(move_line,picking)
            values.append(template)
        return self.env['stock.move'].create(values)