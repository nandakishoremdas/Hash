# -*- coding: utf-8 -*-
{
    'name': 'Sale Margin Analytic',
    'version': '17.0.1.0.0',
    'category': 'Sale',
    'summary': 'Adds margin-based multi-product selection to Sale Orders with '
               'analytic account-aware invoicing.',
    'description': 'Adds multi-product selection with margin on Sale Orders. '
                   'Products are auto-added with increasing quantity and adjusted price. '
                   'Invoices create one service line with analytic distribution '
                   'based on product subtotals.',
    'maintainer': '',
    'company': '',
    'website': '',
    'depends': ['base', 'sale_management', 'stock', 'account_accountant'],
    'data': [
        'data/product_data.xml',
        'views/sale_order_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
