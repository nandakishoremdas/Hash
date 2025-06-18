# -*- coding: utf-8 -*-

from odoo import _, models, SUPERUSER_ID
from odoo.fields import Command
from odoo.addons.sale.wizard.sale_make_invoice_advance import SaleAdvancePaymentInv


class SaleAdvancePaymentInvInherit(models.TransientModel):
    '''Inherited sale.advance.payment.inv class to update methods'''
    _inherit = 'sale.advance.payment.inv'


    def _create_invoices(self, sale_orders):
        '''Monkey patched the method to override the logic'''
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            # Custom logic for creating invoice with custom analytic line
            lines_domain = [('is_downpayment', '=', False), ('display_type', '=', False)]
            invoiceable_domain = lines_domain + [('invoice_status', '=', 'to invoice')]
            invoiceable_lines = sale_orders.order_line.filtered_domain(invoiceable_domain)
            analytic_plan = self.env['account.analytic.plan'].create({'name': 'Analytic - ' + sale_orders.name +' (Sale plan)'})
            analytic_dict = {}
            for line in invoiceable_lines:
                analytic_account = self.env['account.analytic.account'].create({
                    'name': 'Analytic - ' + line.product_id.name +' (service plan)',
                    'plan_id': analytic_plan.id,
                    'company_id': False,
                })
                analytic_dict[analytic_account.id] = line.price_total / sale_orders.amount_total * 100

            invoiceable_lines.invoice_status = 'invoiced'
            invoice_vals = sale_orders._prepare_invoice()
            invoice_vals['invoice_line_ids'] = [(0, 0, {
                'display_type': 'product',
                'name': "Analytic",
                'product_id': self.env.ref('sale_margin_analytic.product_product_analytic_demo').id,
                'quantity': 1,
                'price_unit': sale_orders.amount_total,
                'sale_line_ids': [Command.link(invoiceable_lines.ids[0])],
                'is_downpayment': False,
                'analytic_distribution':analytic_dict,
            })]
            moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals)
            return moves
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            # Create deposit product if necessary
            if not self.product_id:
                self.company_id.sudo().sale_down_payment_product_id = self.env['product.product'].create(
                    self._prepare_down_payment_product_values()
                )
                self._compute_product_id()

            # Create down payment section if necessary
            SaleOrderline = self.env['sale.order.line'].with_context(sale_no_log_for_new_lines=True)
            if not any(line.display_type and line.is_downpayment for line in order.order_line):
                SaleOrderline.create(
                    self._prepare_down_payment_section_values(order)
                )

            down_payment_lines = SaleOrderline.create(
                self._prepare_down_payment_lines_values(order)
            )

            invoice = self.env['account.move'].sudo().create(
                self._prepare_invoice_values(order, down_payment_lines)
            )

            # Ensure the invoice total is exactly the expected fixed amount.
            if self.advance_payment_method == 'fixed':
                delta_amount = (invoice.amount_total - self.fixed_amount) * (1 if invoice.is_inbound() else -1)
                if not order.currency_id.is_zero(delta_amount):
                    receivable_line = invoice.line_ids\
                        .filtered(lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
                    product_lines = invoice.line_ids\
                        .filtered(lambda aml: aml.display_type == 'product')
                    tax_lines = invoice.line_ids\
                        .filtered(lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))

                    if product_lines and tax_lines and receivable_line:
                        line_commands = [Command.update(receivable_line.id, {
                            'amount_currency': receivable_line.amount_currency + delta_amount,
                        })]
                        delta_sign = 1 if delta_amount > 0 else -1
                        for lines, attr, sign in (
                            (product_lines, 'price_total', -1),
                            (tax_lines, 'amount_currency', 1),
                        ):
                            remaining = delta_amount
                            lines_len = len(lines)
                            for line in lines:
                                if order.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                    break
                                amt = delta_sign * max(
                                    order.currency_id.rounding,
                                    abs(order.currency_id.round(remaining / lines_len)),
                                )
                                remaining -= amt
                                line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                        invoice.line_ids = line_commands

            # Unsudo the invoice after creation if not already sudoed
            invoice = invoice.sudo(self.env.su)

            poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': invoice, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )

            title = _("Down payment invoice")
            order.with_user(poster).message_post(
                body=_("%s has been created", invoice._get_html_link(title=title)),
            )

            return invoice

    SaleAdvancePaymentInv._create_invoices = _create_invoices
