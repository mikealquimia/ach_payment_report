# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    document_date = fields.Date(string="Document date")

class AccountPayment(models.Model):
    _inherit = 'account.invoice'

    mapped_sale = fields.Boolean(string="Mapped Sale")