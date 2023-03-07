# -*- coding: utf-8 -*-
{
    'name': "Payment Report",

    'summary': """Report to sales and payments to date""",
    'description': """Report to sales and payments to date""",
    'author': "ACH",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base','sale','account','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'reports/report_payment_action.xml',
        'reports/report_payment.xml',
        'views/cash_sale_views.xml',
    ],
}