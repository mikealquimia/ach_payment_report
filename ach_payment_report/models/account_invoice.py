# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    last_payment = fields.Date(string="Last Payment", related='payment_ids.payment_date', store=True, copied="1")