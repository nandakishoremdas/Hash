# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    '''Inherited sale.order class to add custom methods'''
    _inherit = 'sale.order'

    product_ids = fields.Many2many('product.product', string="Products")
    extra_margin = fields.Float(string="Extra Margin")

    @api.constrains('product_ids')
    def update_product_ids(self):
        '''Upon saving the sale_order record the method triggers'''
        i = 1
        self.order_line = [fields.Command.clear()]
        for pro in self.product_ids:
            self.write({
                'order_line': [
                    (0, 0, {
                        'product_id': pro.id,
                        'product_uom_qty': i,
                        'price_unit': pro.list_price + self.extra_margin,
                    })],
            })
            i+=1
