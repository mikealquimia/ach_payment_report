# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    ret_ext = fields.Boolean(string="Ret/Ext")