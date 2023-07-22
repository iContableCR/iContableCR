import base64
import re
import datetime
import pytz
import json

from xml.sax.saxutils import escape
from odoo.addons.cr_electronic_invoice.models import api_facturae
from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    xml_timbre = fields.Binary("Archivo Timbre Od.")

    economic_activity_id = fields.Many2one(
        domain="[('active','=',True)]", required=True
    )
    is_timbre = fields.Boolean("Es timbre",compute="_compute_is_timbre")
    payment_reference = fields.Char(related="sequence")
    @api.depends("invoice_line_ids","invoice_line_ids.product_id")
    def _compute_is_timbre(self):
        for record in self:
            line_timbre = self.invoice_line_ids.filtered(lambda l:l.product_id.exent_product)
            if line_timbre:
                record.is_timbre = True
            else:
                record.is_timbre = False

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):        
        for record in self:
            if record.is_timbre:
                line_id = record.invoice_line_ids.filtered(lambda l:l.product_id.id == self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id)
                if line_id:
                    record.invoice_line_ids = [(2,line_id[0].id,0)]
                priceu = sum(record.invoice_line_ids.filtered(lambda l:l.product_id.id != self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id and l.product_id.exent_product).mapped("price_subtotal")) *.05    
                record.invoice_line_ids = [(0,0,{
                    "product_id": self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id,
                    "name": self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").name,
                    "price_unit": priceu,
                    "quantity": 1,
                    "price_subtotal": priceu,
                })]
                record.invoice_line_ids[-1]._onchange_price_subtotal()
                
            else:
                line_id = record.invoice_line_ids.filtered(lambda l:l.product_id.id == self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id)
                if line_id:
                    record.invoice_line_ids = [(2,line_id[0].id,0)]
        return super(AccountMove,self)._onchange_invoice_line_ids()

    
    def generate_and_send_invoices(self, invoices):
        def cleanhtml(raw_html):
            CLEANR = re.compile('<.*?>')
            cleantext = re.sub(CLEANR, '', raw_html)
            return cleantext
        total_invoices = len(invoices)
        current_invoice = 0

        days_left = self.env.user.company_id.get_days_left()
        message = self.env.user.company_id.get_message_to_send()
        days_left=1
        for inv in invoices:
            try:
                current_invoice += 1

                if days_left <= self.env.user.company_id.range_days:
                    print('1')
                    #inv.message_post(
                    #    body=message,
                    #    subject=_('IMPORTANT NOTICE!!'),
                    #    message_type='notification',
                    #    subtype=None,
                    #    parent_id=False,
                    #)

                if not inv.sequence or not inv.sequence.isdigit():  # or (len(inv.number) == 10):
                    inv.state_tributacion = 'na'
                    _logger.info('E-INV CR - Ignored invoice:%s', inv.number_electronic)
                    continue

                _logger.debug('generate_and_send_invoices - Invoice %s / %s  -  number:%s',
                              current_invoice, total_invoices, inv.number_electronic)

                if not inv.xml_comprobante or (inv.tipo_documento == 'FEC' and inv.state_tributacion == 'rechazado'):

                    if inv.tipo_documento == 'FEC' and inv.state_tributacion == 'rechazado':
                        msg_body = _('Another FEC is being sent because the previous one was rejected by Hacienda. ')
                        msg_body += _('Attached the previous XMLs. Previous key: ')
                        fname_xml_respuesta_tributacion = inv.fname_xml_respuesta_tributacion.copy()
                        fname_xml_comprobante = inv.fname_xml_comprobante.copy()
                        inv.message_post(
                            body=msg_body + inv.number_electronic,
                            subject=_('Sending a second FEC'),
                            message_type='notification',
                            subtype=None,
                            parent_id=False,
                            attachments=[
                                [
                                    fname_xml_respuesta_tributacion,
                                    fname_xml_respuesta_tributacion
                                ],
                                [
                                    fname_xml_comprobante,
                                    fname_xml_comprobante
                                ]
                            ]
                        )

                        sequence = inv.company_id.FEC_sequence_id.next_by_id()
                        response_json = api_facturae.get_clave_hacienda(self,
                                                                        inv.tipo_documento,
                                                                        sequence,
                                                                        inv.journal_id.sucursal,
                                                                        inv.journal_id.terminal)

                        inv.number_electronic = response_json.get('clave')
                        inv.sequence = response_json.get('consecutivo')

                    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
                    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
                    dia = inv.number_electronic[3:5]  # '%02d' % now_cr.day,
                    mes = inv.number_electronic[5:7]  # '%02d' % now_cr.month,
                    anno = inv.number_electronic[7:9]  # str(now_cr.year)[2:4],

                    date_cr = now_cr.strftime("20" + anno + "-" + mes + "-" + dia + "T%H:%M:%S-06:00")

                    inv.date_issuance = date_cr

                    numero_documento_referencia = False
                    fecha_emision_referencia = False
                    codigo_referencia = False
                    tipo_documento_referencia = False
                    razon_referencia = False
                    currency = inv.currency_id
                    invoice_comments = escape(cleanhtml(inv.narration)) if inv.narration else ''

                    if (inv.invoice_id or inv.not_loaded_invoice) and \
                       inv.reference_code_id and inv.reference_document_id:
                        if inv.invoice_id:
                            if inv.invoice_id.number_electronic and inv.invoice_line_ids[0].product_id:
                                numero_documento_referencia = inv.invoice_id.number_electronic
                                fecha_emision_referencia = inv.invoice_id.date_issuance or inv.invoice_id.invoice_date.strftime("%Y-%m-%d") + "T12:00:00-06:00"
                            else:
                                numero_documento_referencia = inv.invoice_id and \
                                    re.sub('[^0-9]+', '', inv.invoice_id.sequence) or re.sub('[^0-9]+', '', inv.invoice_id.name)
                                invoice_date = inv.invoice_id.invoice_date
                                fecha_emision_referencia = invoice_date.strftime("%Y-%m-%d") + "T12:00:00-06:00"
                        else:
                            numero_documento_referencia = inv.not_loaded_invoice
                            fecha_emision_referencia = inv.not_loaded_invoice_date.strftime("%Y-%m-%d")
                            fecha_emision_referencia += "T12:00:00-06:00"
                        tipo_documento_referencia = inv.reference_document_id.code
                        codigo_referencia = inv.reference_code_id.code
                        razon_referencia = inv.reference_code_id.name

                    if inv.invoice_payment_term_id:
                        sale_conditions = inv.invoice_payment_term_id.sale_conditions_id and \
                            inv.invoice_payment_term_id.sale_conditions_id.code or '01'
                    else:
                        sale_conditions = '01'

                    # Validate if invoice currency is the same as the company currency
                    if currency.name == self.company_id.currency_id.name:
                        currency_rate = 1
                    else:
                        # currency_rate = round(1.0 / currency.rate, 5)
                        custom_rate = currency.rate_ids.search([('name','=',fields.Date.today())],limit=1)
                        currency_rate = round(1.0 / currency.rate, 5)
                        if custom_rate:
                            currency_rate = round(1.0 / custom_rate.inverse_original_rate_2, 5)
                        

                    # Generamos las líneas de la factura
                    lines = dict([])
                    otros_cargos = dict([])
                    otros_cargos_id = 0
                    line_number = 0
                    total_otros_cargos = 0.0
                    total_iva_devuelto = 0.0
                    total_servicio_salon = 0.0
                    total_servicio_gravado = 0.0
                    total_servicio_exento = 0.0
                    total_servicio_exonerado = 0.0
                    total_mercaderia_gravado = 0.0
                    total_mercaderia_exento = 0.0
                    total_mercaderia_exonerado = 0.0
                    total_descuento = 0.0
                    total_impuestos = 0.0
                    base_subtotal = 0.0
                    _no_cabys_code = False

                    for inv_line in inv.invoice_line_ids.filtered(lambda x: not x.display_type):

                        # Revisamos si está línea es de Otros Cargos
                        env_iva_devuelto = self.env.ref('cr_electronic_invoice.product_iva_devuelto').id
                        if inv_line.product_id and inv_line.product_id.id == env_iva_devuelto:
                            total_iva_devuelto = -inv_line.price_total                        
                        # elif inv_line.product_id and inv_line.product_id.categ_id.name == 'Otros Cargos':
                        elif inv_line.product_id and inv_line.product_id.id == self.env.ref("l10n_cr_timbre_odontologico.product_product_timbreodo").id:
                            otros_cargos_id += 1
                            otros_cargos[otros_cargos_id] = {
                                'TipoDocumento': '07',
                                'Detalle': escape(inv_line.name[:150]),
                                'MontoCargo': inv_line.price_total
                            }
                            if inv_line.third_party_id:
                                otros_cargos[otros_cargos_id]['NombreTercero'] = inv_line.third_party_id.name

                                if inv_line.third_party_id.vat:
                                    otros_cargos[otros_cargos_id]['NumeroIdentidadTercero'] = \
                                        inv_line.third_party_id.vat

                            total_otros_cargos += inv_line.price_total

                        else:
                            line_number += 1
                            price = inv_line.price_unit
                            quantity = inv_line.quantity
                            if not quantity:
                                continue

                            line_taxes = inv_line.tax_ids.compute_all(
                                price, currency, 1,
                                product=inv_line.product_id,
                                partner=inv_line.move_id.partner_id)

                            price_unit = round(line_taxes['total_excluded'], 5)

                            base_line = round(price_unit * quantity, 5)
                            descuento = inv_line.discount and round(
                                price_unit * quantity * inv_line.discount / 100.0,
                                5) or 0.0

                            subtotal_line = round(base_line - descuento, 5)

                            # Corregir error cuando un producto trae en el nombre "", por ejemplo: "disco duro"
                            # Esto no debería suceder, pero, si sucede, lo corregimos
                            if inv_line.name[:156].find('"'):
                                detalle_linea = inv_line.name[:160].replace(
                                    '"', '')

                            line = {
                                "cantidad": quantity,
                                "detalle": escape(detalle_linea),
                                "precioUnitario": price_unit,
                                "montoTotal": base_line,
                                "subtotal": subtotal_line,
                                "BaseImponible": subtotal_line,
                                "unidadMedida": inv_line.product_uom_id and inv_line.product_uom_id.code or 'Sp'
                            }

                            if inv_line.product_id:
                                line["codigo"] = inv_line.product_id.default_code or ''
                                line["codigoProducto"] = inv_line.product_id.code or ''

                                if inv_line.product_id.cabys_code:
                                    line["codigoCabys"] = inv_line.product_id.cabys_code
                                elif inv_line.product_id.categ_id and inv_line.product_id.categ_id.cabys_code:
                                    line["codigoCabys"] = inv_line.product_id.categ_id.cabys_code
                                else:
                                    _no_cabys_code = _(f'Warning!.\nLine without CABYS code: {inv_line.name}')
                                    continue
                            else:
                                _no_cabys_code = _(f'Warning!.\nLine without CABYS code: {inv_line.name}')
                                continue

                            if inv.tipo_documento == 'FEE' and inv_line.tariff_head:
                                line["partidaArancelaria"] = inv_line.tariff_head

                            if inv_line.discount and price_unit > 0:
                                total_descuento += descuento
                                line["montoDescuento"] = descuento
                                line["naturalezaDescuento"] = inv_line.discount_note or 'Descuento Comercial'

                            # Se generan los impuestos
                            taxes = dict([])
                            _line_tax = 0.0
                            _tax_exoneration = False
                            _percentage_exoneration = 0
                            if inv_line.tax_ids:
                                tax_index = 0

                                taxes_lookup = {}
                                for i in inv_line.tax_ids:
                                    if i.has_exoneration:
                                        _tax_exoneration = True
                                        _tax_rate = i.tax_root.amount
                                        _tax_exoneration_rate = min(i.percentage_exoneration, _tax_rate)
                                        _percentage_exoneration = _tax_exoneration_rate / _tax_rate
                                        taxes_lookup[i.id] = {'tax_code': i.tax_root.tax_code,
                                                              'tarifa': _tax_rate,
                                                              'iva_tax_desc': i.tax_root.iva_tax_desc,
                                                              'iva_tax_code': i.tax_root.iva_tax_code,
                                                              'exoneration_percentage': _tax_exoneration_rate,
                                                              'amount_exoneration': i.amount}
                                    else:
                                        taxes_lookup[i.id] = {'tax_code': i.tax_code,
                                                              'tarifa': i.amount,
                                                              'iva_tax_desc': i.iva_tax_desc,
                                                              'iva_tax_code': i.iva_tax_code}

                                for i in line_taxes['taxes']:
                                    if taxes_lookup[i['id']]['tax_code'] == 'service':
                                        total_servicio_salon += round(
                                            subtotal_line * taxes_lookup[i['id']]['tarifa'] / 100, 5)

                                    elif taxes_lookup[i['id']]['tax_code'] != '00':
                                        tax_index += 1
                                        tax_amount = round(subtotal_line * taxes_lookup[i['id']]['tarifa'] / 100, 5)
                                        _line_tax += tax_amount
                                        tax = {
                                            'codigo': taxes_lookup[i['id']]['tax_code'],
                                            'tarifa': taxes_lookup[i['id']]['tarifa'],
                                            'monto': tax_amount,
                                            'iva_tax_desc': taxes_lookup[i['id']]['iva_tax_desc'],
                                            'iva_tax_code': taxes_lookup[i['id']]['iva_tax_code'],
                                        }
                                        # Se genera la exoneración si existe para este impuesto
                                        if _tax_exoneration:
                                            exoneration_percentage = taxes_lookup[i['id']]['exoneration_percentage']
                                            _tax_amount_exoneration = round(subtotal_line *
                                                                            exoneration_percentage / 100, 5)

                                            _line_tax -= _tax_amount_exoneration

                                            tax["exoneracion"] = {
                                                "montoImpuesto": _tax_amount_exoneration,
                                                "porcentajeCompra": int(exoneration_percentage)
                                            }

                                        taxes[tax_index] = tax

                                line["impuesto"] = taxes
                                line["impuestoNeto"] = round(_line_tax, 5)

                            # Si no hay product_uom_id se asume como Servicio
                            if not inv_line.product_uom_id or \
                                inv_line.product_uom_id.category_id.name in ('Service',
                                                                             'Services',
                                                                             'Servicio',
                                                                             'Servicios'):
                                if taxes:
                                    if _tax_exoneration:
                                        if _percentage_exoneration < 1:
                                            total_servicio_gravado += (base_line * (1 - _percentage_exoneration))
                                        total_servicio_exonerado += (base_line * _percentage_exoneration)

                                    else:
                                        total_servicio_gravado += base_line

                                    total_impuestos += _line_tax
                                else:
                                    total_servicio_exento += base_line
                            else:
                                if taxes:
                                    if _tax_exoneration:
                                        if _percentage_exoneration < 1:
                                            total_mercaderia_gravado += (base_line * (1 - _percentage_exoneration))
                                        total_mercaderia_exonerado += (base_line * _percentage_exoneration)

                                    else:
                                        total_mercaderia_gravado += base_line

                                    total_impuestos += _line_tax
                                else:
                                    total_mercaderia_exento += base_line

                            base_subtotal += subtotal_line

                            line["montoTotalLinea"] = round(subtotal_line + _line_tax, 5)

                            lines[line_number] = line

                    if total_servicio_salon:
                        total_servicio_salon = round(total_servicio_salon, 5)
                        total_otros_cargos += total_servicio_salon
                        otros_cargos_id += 1
                        otros_cargos[otros_cargos_id] = {
                            'TipoDocumento': '06',
                            'Detalle': escape('Servicio salon 10%'),
                            'MontoCargo': total_servicio_salon
                        }

                    # TODO: CORREGIR BUG NUMERO DE FACTURA NO SE
                    # GUARDA EN LA REFERENCIA DE LA NC CUANDO SE CREA MANUALMENTE
                    if inv.invoice_id and not inv.invoice_origin:
                        inv.invoice_origin = inv.invoice_id.display_name

                    if _no_cabys_code and inv.tipo_documento != 'NC':  # CAByS is not required for financial NCs
                        inv.state_tributacion = 'error'
                        inv.message_post(subject=_('Error'), body=_no_cabys_code)
                        continue

                    if abs(base_subtotal + total_impuestos +
                           total_otros_cargos - total_iva_devuelto - inv.amount_total) > 0.5:
                        inv.state_tributacion = 'error'
                        inv.message_post(
                            subject=_('Error'),
                            body=_('Invoice amount does not match amount for XML. '
                                   'Invoice: %s XML:%s base:%s VAT:%s otros_cargos:%s iva_devuelto:%s') % (
                                       inv.amount_total, (base_subtotal + total_impuestos +
                                                          total_otros_cargos - total_iva_devuelto),
                                       base_subtotal, total_impuestos, total_otros_cargos, total_iva_devuelto))
                        continue
                    total_servicio_gravado = round(total_servicio_gravado, 5)
                    total_servicio_exento = round(total_servicio_exento, 5)
                    total_servicio_exonerado = round(total_servicio_exonerado, 5)
                    total_mercaderia_gravado = round(total_mercaderia_gravado, 5)
                    total_mercaderia_exento = round(total_mercaderia_exento, 5)
                    total_mercaderia_exonerado = round(total_mercaderia_exonerado, 5)
                    total_otros_cargos = round(total_otros_cargos, 5)
                    total_iva_devuelto = round(total_iva_devuelto, 5)
                    base_subtotal = round(base_subtotal, 5)
                    total_impuestos = round(total_impuestos, 5)
                    total_descuento = round(total_descuento, 5)
                    # ESTE METODO GENERA EL XML DIRECTAMENTE DESDE PYTHON
                    xml_string_builder = api_facturae.gen_xml_v43(
                        inv, sale_conditions, total_servicio_gravado,
                        total_servicio_exento, total_servicio_exonerado,
                        total_mercaderia_gravado, total_mercaderia_exento,
                        total_mercaderia_exonerado, total_otros_cargos, total_iva_devuelto, base_subtotal,
                        total_impuestos, total_descuento, lines,
                        otros_cargos, currency_rate, invoice_comments,
                        tipo_documento_referencia, numero_documento_referencia,
                        fecha_emision_referencia, codigo_referencia, razon_referencia)

                    xml_to_sign = str(xml_string_builder)
                    xml_firmado = api_facturae.sign_xml(
                        inv.company_id.signature,
                        inv.company_id.frm_pin,
                        xml_to_sign)
                    ###inv.company_id.frm_ws_password
                    # inv.xml_comprobante = base64.b64encode(xml_firmado)
                    inv.fname_xml_comprobante = inv.tipo_documento + '_' + inv.number_electronic + '.xml'
                    self.env['ir.attachment'].sudo().create({'name': inv.fname_xml_comprobante,
                                                             'type': 'binary',
                                                             'datas': base64.b64encode(xml_firmado),
                                                             'res_model': self._name,
                                                             'res_id': inv.id,
                                                             'res_field': 'xml_comprobante',
                                                             'res_name': inv.fname_xml_comprobante,
                                                             'mimetype': 'text/xml'})

                    _logger.info('E-INV CR - SIGNED XML:%s', inv.fname_xml_comprobante)
                else:
                    xml_firmado = inv.xml_comprobante

                # Get token from Hacienda
                token_m_h = api_facturae.get_token_hacienda(inv, inv.company_id.frm_ws_ambiente)

                response_json = api_facturae.send_xml_fe(inv, token_m_h, inv.date_issuance,
                                                         xml_firmado, inv.company_id.frm_ws_ambiente)

                response_status = response_json.get('status')
                response_text = response_json.get('text')

                if 200 <= response_status <= 299:
                    if inv.tipo_documento == 'FEC':
                        inv.state_tributacion = 'procesando'
                    else:
                        inv.state_tributacion = 'procesando'
                    inv.electronic_invoice_return_message = response_text
                else:
                    if response_text.find('ya fue recibido anteriormente') != -1:
                        if inv.tipo_documento == 'FEC':
                            inv.state_tributacion = 'procesando'
                        else:
                            inv.state_tributacion = 'procesando'
                        inv.message_post(subject=_('Error'),
                                         body=_('Already received previously, it is passed to consult'))
                    elif inv.error_count > 10:
                        inv.message_post(subject=_('Error'), body=response_text)
                        inv.electronic_invoice_return_message = response_text
                        inv.state_tributacion = 'error'
                        _logger.error(_(f'E-INV CR  - Invoice: {inv.number_electronic}' +
                                      'Status: {response_status} Error sending XML: {response_text}'))
                    else:
                        inv.error_count += 1
                        if inv.tipo_documento == 'FEC':
                            inv.state_tributacion = 'procesando'
                        else:
                            inv.state_tributacion = 'procesando'
                        inv.message_post(subject=_('Error'), body=response_text)
                        _logger.error(_('E-INV CR  - Invoice: %s  Status: %s Error '
                                      'sending XML: %s' % (inv.number_electronic, response_status, response_text)))
            except Exception as error:
                inv.state_tributacion = 'error'
                inv.message_post(subject=_('Error'),
                                 body=_('Warning!.\n Error in generate_and_send_invoice: ') + str(error))
                continue
    def action_post(self):
        # Revisamos si el ambiente para Hacienda está habilitado
        for inv in self:
            if inv.company_id.frm_ws_ambiente == 'disabled':
                super().action_post()
                inv.tipo_documento = 'disabled'
                continue
            if inv.tipo_documento == 'disabled':
                super().action_post()
                continue

            if inv.partner_id.has_exoneration and inv.partner_id.date_expiration and \
               (inv.partner_id.date_expiration < datetime.date.today()):
                raise UserError(_('The exoneration of this client has expired'))

            currency = inv.currency_id
            sequence = False
            if (inv.invoice_id) and not (inv.reference_code_id and inv.reference_document_id):
                raise UserError(_('Incomplete reference data for credit note'))
            elif (inv.not_loaded_invoice or inv.not_loaded_invoice_date) and not \
                (inv.not_loaded_invoice and inv.not_loaded_invoice_date and
                 inv.reference_code_id and inv.reference_document_id):
                raise UserError(_('Incomplete reference data for credit note not uploaded'))

            if inv.move_type == 'in_invoice' and inv.partner_id.country_id and \
               inv.partner_id.country_id.code == 'CR' and inv.partner_id.identification_id and \
               inv.partner_id.vat and inv.economic_activity_id is False:
                raise UserError(_('FEC invoices require that the supplier has defined the economic activity'))
            # tipo de identificación
            if not inv.company_id.identification_id:
                raise UserError(_('Select the type of issuer identification in the company profile'))

            if inv.partner_id and inv.partner_id.vat:
                identificacion = re.sub('[^0-9]', '', inv.partner_id.vat)
                id_code = inv.partner_id.identification_id and inv.partner_id.identification_id.code
                if not id_code:
                    if len(identificacion) == 9:
                        id_code = '01'
                    elif len(identificacion) == 10:
                        id_code = '02'
                    elif len(identificacion) in (11, 12):
                        id_code = '03'
                    else:
                        id_code = '05'

                if id_code == '01' and len(identificacion) != 9:
                    raise UserError(_("The recipient's Physical ID must have 9 digits"))
                elif id_code == '02' and len(identificacion) != 10:
                    raise UserError(_('The Legal ID of the recipient must have 10 digits'))
                elif id_code == '03' and len(identificacion) not in (11, 12):
                    raise UserError(_("The recipient's DIMEX identification must have 11 or 12 digits"))
                elif id_code == '04' and len(identificacion) != 10:
                    raise UserError(_('The NITE identification of the receiver must have 10 digits'))

            if inv.invoice_payment_term_id and not inv.invoice_payment_term_id.sale_conditions_id:
                raise UserError(_('The electronic invoice could not be created: \n'
                                'You must set up payment terms for %s') % (inv.invoice_payment_term_id.name))

            # Validate if invoice currency is the same as the company currency
            if currency.name != inv.company_id.currency_id.name and (not currency.rate_ids or not
                                                                     (len(currency.rate_ids) > 0)):
                raise UserError(_(f'There is no registered exchange rate for the currency {currency.name}'))

            # Digital Invoice or ticket
            if inv.move_type in ('out_invoice', 'out_refund') and inv.number_electronic:
                pass
            else:
                (tipo_documento, sequence) = inv.get_invoice_sequence()
                if tipo_documento and sequence:
                    inv.tipo_documento = tipo_documento
                else:
                    super().action_post()
                    continue

            # Calcular si aplica IVA Devuelto
            # Sólo aplica para clínicas y para pago por tarjeta            
            if inv.payment_methods_id.sequence == '02':
                prod_iva_devuelto = self.env.ref('cr_electronic_invoice.product_iva_devuelto')
                iva_devuelto = 0
                for inv_line in inv.invoice_line_ids:
                    if inv_line.product_id.service_medic and self.env.ref('cr_electronic_invoice.iva_tax_07').id in inv_line.tax_ids.ids and len(inv_line.tax_ids.ids)==1:
                        # # Remove any existing IVA Devuelto lines
                        # if inv_line.product_id.id == prod_iva_devuelto.id:
                        #     inv_line.unlink
                        # elif inv_line.product_id.categ_id.name == 'Servicios de Salud':
                            iva_devuelto += (inv_line.price_total-inv_line.price_subtotal)
                if iva_devuelto:
                    line_iva = inv.invoice_line_ids.filtered(lambda l:l.product_id.id == prod_iva_devuelto.id)
                    if line_iva:
                        inv.invoice_line_ids = [(5,0,line_iva[0].id)]
                    inv.invoice_line_ids = [(0,0,{
                        'name': 'IVA Devuelto',                                                
                        'product_id': prod_iva_devuelto.id,
                        'account_id': prod_iva_devuelto.property_account_income_id.id,
                        'price_unit': -iva_devuelto,
                        'quantity': 1,
                        'price_total': -iva_devuelto,
                    })]

            super().action_post()
            if not inv.number_electronic:
                # if journal doesn't have sucursal use default from company
                sucursal_id = inv.journal_id.sucursal or self.env.user.company_id.sucursal_MR

                # if journal doesn't have terminal use default from company
                terminal_id = inv.journal_id.terminal or self.env.user.company_id.terminal_MR                
                response_json = api_facturae.get_clave_hacienda(inv,
                                                                inv.tipo_documento,
                                                                sequence,
                                                                sucursal_id,
                                                                terminal_id)

                inv.number_electronic = response_json.get('clave')
                inv.sequence = response_json.get('consecutivo')

            inv.name = inv.sequence
            inv.state_tributacion = False
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    @api.onchange('product_id')
    def _onchange_product_id_timbre(self):
        return {'domain': {'product_id': [('id','in', self.env["product.product"].search([('economic_activity_id','=',self.move_id.economic_activity_id.id)]).ids)]}}