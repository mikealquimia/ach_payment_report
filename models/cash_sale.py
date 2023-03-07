# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CashSale(models.TransientModel):
    _name = 'cash.sale'
    _description = 'Cash Sale'

    name = fields.Char(string='Movimiento de Caja')
    date = fields.Date(string='Fecha')
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.user.company_id)

    def get_pdf(self):
        return self.env.ref('ach_payment_report.action_pdf_cash_sale').report_action(self)
    
