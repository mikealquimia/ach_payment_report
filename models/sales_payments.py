# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime,timedelta
import pytz

class SalePayment(models.TransientModel):
    _name = 'sale.payment'
    _description = 'Sale Payment Report'

    name = fields.Char(string="Sales Payments")
    date = fields.Date(string='Date')
    journal_ids = fields.Many2many('account.journal', string="Journals")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    def get_pdf(self):
        return self.env.ref('ach_payment_report.action_pdf_sale_payment_ach').report_action(self)
    
    def sale_day_lines(self, date):
        #Set Payment to Sales in date
        so_day_lines = []
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        date_start_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 0, 0, 59)).astimezone(tz)
        date_stop_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 23, 59, 59)).astimezone(tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = "select so.name as so_name, "
        query += "coalesce(string_agg(invoices.numb,','),'') as invo, "
        query += "so.amount_total as sale_amount, "
        query += "rp.name as partner, "
        query += "coalesce(sum(payment_so.amou),0) as so_pa_d, coalesce(string_agg(journals.paname,','),'') as so_pa_d_aj, coalesce(sum(payment_so_t.amou),0) as so_pa_notd, "
        query += "coalesce(sum(invoices.ai_pay),0) as inv_pay_d, coalesce(string_agg(invoices.j2_name,','),'') as inv_pa_d_aj, coalesce(sum(invoices.amou_total),0) as inv_pay_total, "
        query += "coalesce(coalesce(sum(payment_so.amou), 0)+coalesce(sum(invoices.amou_total), 0),0) as payment_total, "
        query += "so.amount_total-(coalesce(coalesce(sum(payment_so.amou), 0)+coalesce(sum(invoices.amou_total), 0),0)) as residual_total "
        query += "from sale_order so "
        query += "inner join res_partner rp on rp.id = so.partner_id "
        query += "left join ( "
        query += "	select sum(ap.amount) as amou, ap.sale_id, ap.journal_id  "
        query += "	from account_payment ap "
        query += "	where ap.state_sale_invoice = 'no_add' and ap.payment_date = %s "
        query += "	group by ap.sale_id, ap.journal_id "
        query += ") as payment_so "
        query += "on payment_so.sale_id = so.id "
        query += "left join ( "
        query += "	select sum(ap4.amount) as amou, ap4.sale_id   "
        query += "	from account_payment ap4 "
        query += "	where ap4.state_sale_invoice = 'no_add' and ap4.payment_date != %s "
        query += "	group by ap4.sale_id  "
        query += ") as payment_so_t "
        query += "on payment_so_t.sale_id = so.id "
        query += "left join ( "
        query += "	select aj.name as paname, aj.id  "
        query += "	from account_journal aj "
        query += "	) as journals "
        query += "on journals.id = payment_so.journal_id "
        query += "left join account_invoice_sale_order_rel aisor on aisor.sale_order_id = so.id "
        query += "left join ( "
        query += "	select ai.number as numb, sum(payment_ai.amou) as ai_pay, ai.id, string_agg(journals2.paname,',') as j2_name , sum(payment_ai3.amou) as amou_total "
        query += "	from account_invoice ai "
        query += "	left join account_invoice_payment_rel aipr on aipr.invoice_id = ai.id "
        query += "	left join ( "
        query += "		select ap3.amount as amou, ap3.id  "
        query += "		from account_payment ap3 "
        query += "		group by ap3.id "
        query += "		) as payment_ai3 "
        query += "	on payment_ai3.id = aipr.payment_id "
        query += "	left join ( "
        query += "		select ap2.amount as amou, ap2.id, ap2.journal_id as journal_id2 "
        query += "		from account_payment ap2 "
        query += "		where ap2.payment_date = %s "
        query += "		group by ap2.id "
        query += "		) as payment_ai "
        query += "	on payment_ai.id = aipr.payment_id "
        query += "	left join ("
        query += "		select aj2.name as paname, aj2.id  "
        query += "		from account_journal aj2 "
        query += "		) as journals2 "
        query += "	on journals2.id = payment_ai.journal_id2  "
        query += "	group by ai.number, ai.id "
        query += "	) as invoices "
        query += "on invoices.id = aisor.account_invoice_id  "
        query += "where so.confirmation_date between %s and %s "
        query += "group by so.name, rp.name, so.amount_total "
        query += "order by so.name "
        params = (date_q, date_q, date_q, date_q_start, date_q_stop)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'name': line['so_name'],
                'invoice': line['invo'],
                'partner': line['partner'],
                'amount': line['sale_amount'],
                'abono': line['so_pa_d']+line['inv_pay_d'],
                'residual': line['residual_total'],
                'ext_ret': 0,
                'journal_id': str(line['so_pa_d_aj'])+ str(line['inv_pa_d_aj']),
                'date_payment': False,
            }
            so_day_lines.append(vals)
        return so_day_lines
    
    def invoice_day_payment(self,date):
        #Invoices confirmed in date but without payment, related sale has a confirmation date different in search date 
        invoice_day_lines = []
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        date_start_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 0, 0, 59)).astimezone(tz)
        date_stop_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 23, 59, 59)).astimezone(tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = "SELECT DISTINCT ai.date as date, ai.number as invoice, ai.residual_signed as residual, "
        query += "so.name as sale_name, so.amount_total as amount_total, rp.name as partner, "
        query += "SUM(apd.amount) as payment_day, "
        query += "string_agg(aj.name,',') as journals, "
        query += "string_agg(apd.payment_date_real::character varying,',') as dates, "
        query += "(so.amount_total-ai.residual_signed) as payment_total "
        query += "FROM account_invoice ai "
        query += "INNER JOIN account_invoice_payment_rel apr on apr.invoice_id = ai.id "
        query += "INNER JOIN account_payment apd on apr.payment_id = apd.id "
        query += "AND apd.payment_date = %s "
        query += "AND apd.state in ('posted', 'send') "
        query += "INNER JOIN account_journal aj on apd.journal_id = aj.id "
        query += "AND apd.payment_date = %s "
        query += "AND apr.payment_id = apd.id "
        query += "INNER JOIN res_partner rp on rp.id = ai.partner_id "
        query += "INNER JOIN account_invoice_sale_order_rel acsor on acsor.account_invoice_id = ai.id "
        query += "INNER JOIN sale_order so on so.id = acsor.sale_order_id "
        query += "AND so.confirmation_date between %s and %s "
        query += "WHERE ai.state in ('open', 'in_payment') "
        query += "GROUP BY ai.date, ai.number, rp.name, so.name, so.amount_total, ai.residual_signed "
        query += "ORDER BY ai.date "
        params = (date_q, date_q, date_q_start, date_q_stop)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale_name': line['sale_name'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount_total': line['amount_total'],
                'payment_day':line['payment_day'],
                'payment_total': line['payment_total'],
                'residual': line['residual'],
                'journals': line['journals'],
                'dates': line['dates'],
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines
    
    def invoice_other_day_payment(self,date):
        #Invoices with payment in search date but with residual, related sale has a confirmation date different in search date 
        invoice_other_day_lines = []
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        date_start_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 0, 0, 59)).astimezone(tz)
        date_stop_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 23, 59, 59)).astimezone(tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = "SELECT DISTINCT ai.date as date, ai.number as invoice, ai.residual_signed as residual, "
        query += "so.name as sale_name, so.amount_total as amount_total, rp.name as partner, "
        query += "SUM(apd.amount) as payment_day, "
        query += "string_agg(aj.name,',') as journals, "
        query += "string_agg(apd.payment_date_real::character varying,',') as dates, "
        query += "(so.amount_total-ai.residual_signed) as payment_total "
        query += "FROM account_invoice ai "
        query += "INNER JOIN account_invoice_payment_rel apr on apr.invoice_id = ai.id "
        query += "INNER JOIN account_payment apd on apr.payment_id = apd.id "
        query += "AND apd.payment_date = %s "
        query += "AND apd.state in ('posted', 'send') "
        query += "INNER JOIN account_journal aj on apd.journal_id = aj.id "
        query += "AND apd.payment_date = %s "
        query += "AND apr.payment_id = apd.id "
        query += "INNER JOIN res_partner rp on rp.id = ai.partner_id "
        query += "INNER JOIN account_invoice_sale_order_rel acsor on acsor.account_invoice_id = ai.id "
        query += "INNER JOIN sale_order so on so.id = acsor.sale_order_id "
        query += "AND so.confirmation_date not between %s and %s "
        query += "WHERE ai.state in ('open', 'in_payment') "
        query += "GROUP BY ai.date, ai.number, rp.name, so.name, so.amount_total, ai.residual_signed "
        query += "ORDER BY ai.date "
        params = (date_q, date_q, date_q_start, date_q_stop)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale_name': line['sale_name'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount_total': line['amount_total'],
                'payment_day':line['payment_day'],
                'payment_total': line['payment_total'],
                'residual': line['residual'],
                'journals': line['journals'],
                'dates': line['dates'],
            }
            invoice_other_day_lines.append(vals)
        return invoice_other_day_lines
    
    def invoice_without_residual_payment(self,date):
        #Invoices with payment in search date but without residual, related sale has a confirmation date different in search date 
        invoice_without_residual_payment = []
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        date_start_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 0, 0, 59)).astimezone(tz)
        date_stop_tz = pytz.utc.localize(datetime(date.year, date.month, date.day, 23, 59, 59)).astimezone(tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = "SELECT DISTINCT ai.date as date, ai.number as invoice, ai.residual_signed as residual, "
        query += "so.name as sale_name, so.amount_total as amount_total, rp.name as partner, "
        query += "SUM(apd.amount) as payment_day, "
        query += "string_agg(aj.name,',') as journals, "
        query += "string_agg(apd.payment_date_real::character varying,',') as dates, "
        query += "(so.amount_total-ai.residual_signed) as payment_total "
        query += "FROM account_invoice ai "
        query += "INNER JOIN account_invoice_payment_rel apr on apr.invoice_id = ai.id "
        query += "INNER JOIN account_payment apd on apr.payment_id = apd.id "
        query += "AND apd.payment_date = %s "
        query += "AND apd.state in ('posted', 'send') "
        query += "INNER JOIN account_journal aj on apd.journal_id = aj.id "
        query += "AND apd.payment_date = %s "
        query += "AND apr.payment_id = apd.id "
        query += "INNER JOIN res_partner rp on rp.id = ai.partner_id "
        query += "INNER JOIN account_invoice_sale_order_rel acsor on acsor.account_invoice_id = ai.id "
        query += "INNER JOIN sale_order so on so.id = acsor.sale_order_id "
        query += "WHERE ai.state = 'paid' AND ai.residual = 0 "
        query += "GROUP BY ai.date, ai.number, rp.name, so.name, so.amount_total, ai.residual_signed "
        query += "ORDER BY ai.date "
        params = (date_q, date_q)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale_name': line['sale_name'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount_total': line['amount_total'],
                'payment_day':line['payment_day'],
                'payment_total': line['payment_total'],
                'residual': line['residual'],
                'journals': line['journals'],
                'dates': line['dates'],
            }
            invoice_without_residual_payment.append(vals)
        return invoice_without_residual_payment
    