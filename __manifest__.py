# -*- coding: utf-8 -*-
{
    'name': "Sales Payment Report",

    'summary': """Report to sales and payments in invoice of date search""",
    'description': """Report to sales and payments in invoice of date search""",
    'author': "ACH",
    'website': "http://www.yourcompany.com",
    'category': 'Sales',
    'version': '1.1',
    'depends': ['base',
                'sale',
                'account',
                'sale_management',
                'ach_payment_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/map_sales.xml',
        'reports/report_payment_action.xml',
        'reports/report_payment.xml',
        'views/sale_payment_views.xml',
        'views/account_payment_views.xml',
    ],
}