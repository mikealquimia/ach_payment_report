# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime,timedelta
import pytz

class CashSale(models.TransientModel):
    _name = 'cash.sale'
    _description = 'Cash Sale'

    name = fields.Char(string='Cash Sale')
    date = fields.Date(string='Date')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    def get_pdf(self):
        return self.env.ref('ach_payment_report.action_pdf_cash_sale').report_action(self)

    def get_hour_tz(self, tz):
        hour = 6
        return hour

    def sale_day_lines(self, date):
        so_day_lines = []
        hour_tz = self.get_hour_tz(self.env.user.tz)
        date_start_tz = datetime(date.year, date.month, date.day, 0, 0, 1) + timedelta(hours=hour_tz) 
        date_stop_tz = datetime(date.year, date.month, date.day, 23, 59, 59) + timedelta(hours=hour_tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = """
select so.name as sale_order, 
coalesce(string_agg(invoices.numb,','),'') as invoice, 
so.amount_total as sale_amount, 
rp.name as partner, 
coalesce(sum(payment_so.amou),0) as advance_amount, coalesce(string_agg(journals.paname,','),'') as advance_journal, coalesce(sum(payment_so_t.amou),0) as advance_amount_no_add, 
coalesce(sum(invoices.ai_pay),0) as payment_invoice_amount, coalesce(string_agg(invoices.j2_name,','),'') as payment_invoice_journal, coalesce(sum(invoices.amou_total),0) as payment_invoice_total, 
coalesce(coalesce(sum(payment_so.amou), 0)+coalesce(sum(invoices.amou_total), 0),0) as payment_total, 
coalesce(sum(xinvoices.ai_pay),0) as retention, 
so.amount_total-(coalesce(coalesce(sum(payment_so.amou),0)+coalesce(sum(invoices.amou_total),0)+coalesce(sum(xinvoices.ai_pay),0),0)) as residual_total, 
coalesce(string_agg(invoices.payment_date_real,','),'') as payment_date_real 
from sale_order so 
inner join res_partner rp on rp.id = so.partner_id 
left join ( 
	select sum(ap.amount) as amou, ap.sale_id, ap.journal_id 
	from account_payment ap 
	where ap.state_sale_invoice = 'no_add' and ap.payment_date = %s 
	group by ap.sale_id, ap.journal_id 
) as payment_so 
on payment_so.sale_id = so.id 
left join ( 
	select sum(ap4.amount) as amou, ap4.sale_id 
	from account_payment ap4 
	where ap4.state_sale_invoice = 'no_add' and ap4.payment_date <= %s 
	group by ap4.sale_id  
) as payment_so_t 
on payment_so_t.sale_id = so.id 
left join ( 
	select aj.name as paname, aj.id 
	from account_journal aj 
	) as journals 
on journals.id = payment_so.journal_id 
left join account_invoice_sale_order_rel aisor on aisor.sale_order_id = so.id 
left join ( 
	select ai.number as numb, sum(payment_ai.amou) as ai_pay, ai.id, string_agg(journals2.paname,',') as j2_name, string_agg(to_char(payment_ai.payment_date_real,'dd-mm-yy'),',') as payment_date_real, sum(payment_ai3.amou) as amou_total 
	from account_invoice ai 
	left join account_invoice_payment_rel aipr on aipr.invoice_id = ai.id 
	left join ( 
		select ap3.amount as amou, ap3.id 
		from account_payment ap3 
		where ap3.payment_date <= %s 
		group by ap3.id 
		) as payment_ai3 
	on payment_ai3.id = aipr.payment_id 
	left join ( 
		select ap2.amount as amou, ap2.id, ap2.journal_id as journal_id2, ap2.payment_date_real as payment_date_real 
		from account_payment ap2 
		where ap2.payment_date = %s 
		group by ap2.id 
		) as payment_ai 
	on payment_ai.id = aipr.payment_id 
	inner join ( 
		select aj2.name as paname, aj2.id 
		from account_journal aj2 
		where aj2.ret_ext is null
		) as journals2 
	on journals2.id = payment_ai.journal_id2 
	group by ai.number, ai.id 
	) as invoices 
on invoices.id = aisor.account_invoice_id 
left join ( 
	select ai.number as numb, sum(payment_ai.amou) as ai_pay, ai.id, string_agg(journals2.paname,',') as j2_name , sum(payment_ai3.amou) as amou_total 
	from account_invoice ai 
	left join account_invoice_payment_rel aipr on aipr.invoice_id = ai.id 
	left join ( 
		select ap3.amount as amou, ap3.id 
		from account_payment ap3 
		where ap3.payment_date <= %s 
		group by ap3.id 
		) as payment_ai3 
	on payment_ai3.id = aipr.payment_id 
	left join ( 
		select ap2.amount as amou, ap2.id, ap2.journal_id as journal_id2 
		from account_payment ap2 
		where ap2.payment_date = %s 
		group by ap2.id 
		) as payment_ai 
	on payment_ai.id = aipr.payment_id 
	inner join ( 
		select aj2.name as paname, aj2.id 
		from account_journal aj2 
		where aj2.ret_ext = true  
		) as journals2 
	on journals2.id = payment_ai.journal_id2 
	group by ai.number, ai.id 
	) as xinvoices 
on xinvoices.id = aisor.account_invoice_id 
where so.confirmation_date between %s and %s 
group by so.name, rp.name, so.amount_total 
order by so.name; """
        params = (date_q, date_q, date_q, date_q, date_q, date_q, date_q_start, date_q_stop)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'name': line['sale_order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount': line['sale_amount'],
                'advance': line['advance_amount']+line['payment_invoice_amount'],
                'residual': line['residual_total'],
                'ext_ret': line['retention'],
                'journal_id': str(line['advance_journal'])+ str(line['payment_invoice_journal']),
                'date_payment': line['payment_date_real'],
            }
            so_day_lines.append(vals)
        return so_day_lines

    def invoice_without_payment(self,date):
        invoice_day_lines = []
        hour_tz = self.get_hour_tz(self.env.user.tz)
        date_start_tz = datetime(date.year, date.month, date.day, 0, 0, 0) + timedelta(hours=hour_tz)
        date_stop_tz = datetime(date.year, date.month, date.day, 23, 59, 59) + timedelta(hours=hour_tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        print(date_q_start, date_q)
        query = """
select ai.origin as order, ai.number as invoice, ai.amount_total_signed as invoice_amount, 
rp.name as partner, so.amount_total as sale_amount, ai.residual_signed as residual 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice = %s and ai.residual_signed = ai.amount_total_signed """
        params = (date_q_start, date_q)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale_name': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount_total': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'residual': line['residual'],
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines

    def invoice_paid(self,date):
        invoice_day_lines = []
        hour_tz = self.get_hour_tz(self.env.user.tz)
        date_start_tz = datetime(date.year, date.month, date.day, 0, 0, 0) + timedelta(hours=hour_tz)
        date_stop_tz = datetime(date.year, date.month, date.day, 23, 59, 59) + timedelta(hours=hour_tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = """
select distinct string_agg(so.name,',') as order, ai.number as invoice, 
rp.name as partner, sum(so.amount_total) as sale_amount, 
ai.amount_total_signed as invoice_amount, aipr.amount as payment_amount, 
coalesce(xaipr.amount,0) as ret_ext, aipr.journal as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real
from account_invoice ai 
left join (  
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
	string_agg(to_char(ap.payment_date_real,'dd-mm-yy'),',') as payment_date_real 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	inner join account_journal aj 
	on aj.id = ap.journal_id and aj.ret_ext is null 
	group by aipr3.invoice_id 
) as aipr 
on aipr.invoice_id = ai.id 
left join (  
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	inner join account_journal aj 
	on aj.id = ap.journal_id and aj.ret_ext = true 
	group by aipr3.invoice_id 
) as xaipr 
on xaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
inner join res_partner rp 
on rp.id = ai.partner_id 
where ai.residual = 0 and ai.last_payment = %s 
group by ai.number, aipr.amount, rp.name, ai.amount_total_signed, xaipr.amount, 
aipr.journal  """
        params = (date_q, date_q, date_q_start, date_q)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'order': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'sale_amount': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'payment_amount': line['payment_amount'],
                'ret_ext': line['ret_ext'],
                'journal': line['journal'],
                'date_payment': line['payment_date_real'],
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines

    def invoice_partial_paid(self,date):
        invoice_day_lines = []
        hour_tz = self.get_hour_tz(self.env.user.tz)
        date_start_tz = datetime(date.year, date.month, date.day, 0, 0, 0) + timedelta(hours=hour_tz)
        date_stop_tz = datetime(date.year, date.month, date.day, 23, 59, 59) + timedelta(hours=hour_tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = """
select distinct string_agg(so.name,',') as order, ai.number as invoice, 
rp.name as partner, coalesce(sum(so.amount_total),0) as sale_amount, 
coalesce(ai.amount_total_signed,0) as invoice_amount, coalesce(aipr.amount,0) as payment_amount, 
coalesce(xxaipr.amount,0) as payment_total_amount, coalesce(coalesce(ai.amount_total_signed,0)-(coalesce(xxaipr.amount,0)),0) as residual, 
coalesce(xaipr.amount,0) as ret_ext, aipr.journal as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real
from account_invoice ai 
left join (  
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
	string_agg(to_char(ap.payment_date_real,'dd-mm-yy'),',') as payment_date_real 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	inner join account_journal aj 
	on aj.id = ap.journal_id and aj.ret_ext is null 
	group by aipr3.invoice_id 
) as aipr 
on aipr.invoice_id = ai.id 
left join (  
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	inner join account_journal aj 
	on aj.id = ap.journal_id and aj.ret_ext = true 
	group by aipr3.invoice_id 
) as xaipr 
on xaipr.invoice_id = ai.id 
left join (  
	select distinct aipr4.invoice_id as invoice_id, 
	sum(ap2.amount) as amount 
	from account_invoice_payment_rel aipr4
	inner join account_payment ap2 
	on ap2.id = aipr4.payment_id and ap2.payment_date <= %s 
	inner join account_journal aj2 
	on aj2.id = ap2.journal_id and aj2.ret_ext is null 
	group by aipr4.invoice_id 
) as xxaipr 
on xxaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id 
inner join res_partner rp 
on rp.id = ai.partner_id 
where so.confirmation_date < %s and aipr.amount > 0 
and xxaipr.amount < ai.amount_total_signed 
group by ai.number, aipr.amount, rp.name, ai.amount_total_signed, xaipr.amount, 
aipr.journal, xxaipr.amount  """
        params = (date_q, date_q, date_q, date_q_start)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'order': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'sale_amount': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'payment_amount': line['payment_amount'],
                'ret_ext': line['ret_ext'],
                'residual': line['residual'],
                'journal': line['journal'],
                'date_payment': line['payment_date_real'],
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines
    
    def journal_detail(self, date):
        detail_journal_amount = []
        hour_tz = self.get_hour_tz(self.env.user.tz)
        date_start_tz = datetime(date.year, date.month, date.day, 0, 0, 0) + timedelta(hours=hour_tz)
        date_stop_tz = datetime(date.year, date.month, date.day, 23, 59, 59) + timedelta(hours=hour_tz)
        date_str = '%s-%s-%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day)
        str_date_start = '%s-%s-%s %s:%s:%s' % (date_start_tz.year, date_start_tz.month, date_start_tz.day, date_start_tz.hour, date_start_tz.minute, date_start_tz.second)
        str_date_stop = '%s-%s-%s %s:%s:%s' % (date_stop_tz.year, date_stop_tz.month, date_stop_tz.day, date_stop_tz.hour, date_stop_tz.minute, date_stop_tz.second)
        date_q = datetime.strptime(date_str, '%Y-%m-%d')
        date_q_start = datetime.strptime(str_date_start, '%Y-%m-%d %H:%M:%S')
        date_q_stop = datetime.strptime(str_date_stop, '%Y-%m-%d %H:%M:%S')
        query = """
select distinct aj.name as journal, ap.amount as amount 
from account_journal aj 
inner join (
	select ap2.journal_id as journal_id, sum(ap2.amount) as amount 
	from account_payment ap2 
	where ap2.payment_date = '06-05-2023'
	group by ap2.journal_id 
) as ap 
on aj.id = ap.journal_id 
group by aj.name, ap.amount """
        params = (date_q)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'journal': line['journal'],
                'amount': line['amount'],
            }
            detail_journal_amount.append(vals)
        return detail_journal_amount
