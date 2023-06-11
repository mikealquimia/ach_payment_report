# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime,timedelta
import pytz

class CashSale(models.TransientModel):
    _name = 'cash.sale'
    _description = 'Cash Sale'

    name = fields.Char(string='Cash Sale')
    date = fields.Date(string='Date')
    journal_ids = fields.Many2many('account.journal', string="Journal", domain=[('type','=','sale')])
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    def get_pdf(self):
        return self.env.ref('ach_payment_report.action_pdf_cash_sale').report_action(self)

    def get_hour_tz(self, tz):
        hour = 6
        return hour

    def sale_day_lines(self, date):
        so_day_lines = []
        journals = [x.id for x in self.journal_ids]
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
coalesce(string_agg(invoices.payment_date_real,','),'') as payment_date_real, coalesce(string_agg(invoices.payment_document,','),'') as payment_document 
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
	select ai.number as numb, sum(payment_ai.amou) as ai_pay, ai.id, string_agg(journals2.paname,',') as j2_name, string_agg(to_char(payment_ai.payment_date_real,'dd-mm-yy'),',') as payment_date_real, sum(payment_ai3.amou) as amou_total, 
	string_agg(payment_ai.payment_document,',') as payment_document 
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
		select ap2.amount as amou, ap2.id, ap2.journal_id as journal_id2, ap2.payment_date_real as payment_date_real, 
        ap2.description_gp as payment_document 
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
	where ai.journal_id in %s 
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
	where ai.journal_id in %s 
    group by ai.number, ai.id 
	) as xinvoices 
on xinvoices.id = aisor.account_invoice_id 
where so.confirmation_date between %s and %s 
group by so.name, rp.name, so.amount_total 
order by so.name; """
        params = (date_q, date_q, date_q, date_q, tuple(journals), date_q, date_q, tuple(journals), date_q_start, date_q_stop)
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
                'date_payment': line['payment_date_real']+'('+line['payment_document']+')',
            }
            so_day_lines.append(vals)
        return so_day_lines

    def invoice_without_payment(self,date):
        invoice_day_lines = []
        journals = [x.id for x in self.journal_ids]
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
select distinct coalesce(string_agg(so.name,','),'') as order, ai.number as invoice, 
rp.name as partner, coalesce(sum(so.amount_total),0) as sale_amount, 
ai.amount_total_signed as invoice_amount, 
sum(apx.amount) as payment_amount 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
left join (
	select aipr.invoice_id,
	sum(ap2.amount) as amount
	from account_invoice_payment_rel aipr 
	inner join account_payment ap2
	on ap2.id = aipr.payment_id and ap2.payment_date <= %s 
	group by aipr.invoice_id  
) as apx
on apx.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice = %s and ai.journal_id in %s and apx.amount is null 
group by ai.number, ai.amount_total_signed, rp.name """
        params = (date_q, date_q_start, date_q, tuple(journals))
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale_name': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'amount_total': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'residual': line['invoice_amount'],
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines

    def invoice_partial_paid(self,date):
        invoice_day_lines = []
        journals = [x.id for x in self.journal_ids]
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
select distinct coalesce(string_agg(so.name,','),'') as order, ai.number as invoice, 
string_agg(rp.name,',') as partner, coalesce(sum(so.amount_total),0) as sale_amount, 
sum(ai.amount_total_signed) as invoice_amount, 
sum(apx.amount) as payment_amount, 
coalesce(sum(aipr.amount),0) as xpayment_amount, 
coalesce(sum(xaipr.amount),0) as ret_ext, coalesce(string_agg(aipr.journal,','),'') as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real, 
coalesce(string_agg(aipr.payment_document,','),'') as payment_document, 
sum(xxaipr.amount) as payment_day 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
left join (
	select aipr.invoice_id,
	sum(ap2.amount) as amount
	from account_invoice_payment_rel aipr 
	inner join account_payment ap2
	on ap2.id = aipr.payment_id and ap2.payment_date <= %s 
	group by aipr.invoice_id  
) as apx
on apx.invoice_id = ai.id 
left join ( 
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
	string_agg(to_char(ap.payment_date_real,'dd-mm-yy'),',') as payment_date_real, 
    string_agg(ap.description_gp,',') as payment_document 
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
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	group by aipr3.invoice_id 
) as xxaipr 
on xxaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice <= %s and ai.journal_id in %s 
group by ai.number 
having sum(apx.amount) < sum(ai.amount_total_signed) and sum(xxaipr.amount) > 0 
and count(aisor.account_invoice_id)=1 
"""
        params = (date_q, date_q, date_q, date_q, date_q_start, date_q, tuple(journals))
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'order': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'sale_amount': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'payment_amount': line['xpayment_amount'],
                'ret_ext': line['ret_ext'],
                'residual': line['invoice_amount']-line['payment_amount'],
                'journal': line['journal'],
                'date_payment': line['payment_date_real'] + '('+line['payment_date_real']+')',
            }
            invoice_day_lines.append(vals)
        query2 = """
select distinct count(aisor.account_invoice_id) as conteo, coalesce(string_agg(so.name,','),'') as order, ai.number as invoice, 
string_agg(rp.name,',') as partner, coalesce(sum(so.amount_total),0) as sale_amount, 
(sum(ai.amount_total_signed)/count(aisor.account_invoice_id)) as invoice_amount, 
(sum(apx.amount)/count(aisor.account_invoice_id)) as payment_amount, 
coalesce((sum(aipr.amount)/count(aisor.account_invoice_id)),0) as xpayment_amount, 
coalesce(sum(xaipr.amount),0) as ret_ext, coalesce(string_agg(aipr.journal,','),'') as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real, 
coalesce(string_agg(aipr.payment_document,','),'') as payment_document, 
sum(xxaipr.amount) as payment_day 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
left join (
	select aipr.invoice_id,
	sum(ap2.amount) as amount
	from account_invoice_payment_rel aipr 
	inner join account_payment ap2
	on ap2.id = aipr.payment_id and ap2.payment_date <= %s 
	group by aipr.invoice_id  
) as apx
on apx.invoice_id = ai.id 
left join ( 
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
	string_agg(to_char(ap.payment_date_real,'dd-mm-yy'),',') as payment_date_real, 
    string_agg(ap.description_gp,',') as payment_document 
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
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	group by aipr3.invoice_id 
) as xxaipr 
on xxaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice <= %s and ai.journal_id in %s 
group by ai.number 
having sum(apx.amount) < sum(ai.amount_total_signed) and sum(xxaipr.amount) > 0 
and count(aisor.account_invoice_id)>1 
"""
        params2 = (date_q, date_q, date_q, date_q, date_q_start, date_q, tuple(journals))
        self.env.cr.execute(query2, params2)
        for line2 in self.env.cr.dictfetchall():
            vals = {
                'order': line2['order'],
                'invoice': line2['invoice'],
                'partner': line2['partner'],
                'sale_amount': line2['sale_amount'],
                'invoice_amount': line2['invoice_amount'],
                'payment_amount': line2['xpayment_amount'],
                'ret_ext': line2['ret_ext'],
                'residual': line2['invoice_amount']-line2['payment_amount'],
                'journal': line2['journal'],
                'date_payment': line2['payment_date_real'] + '('+line2['payment_date_real']+')',
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines

    def invoice_paid(self,date):
        invoice_day_lines = []
        journals = [x.id for x in self.journal_ids]
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
select distinct coalesce(string_agg(so.name,','),'') as order, ai.number as invoice, 
string_agg(rp.name,',') as partner, coalesce(sum(so.amount_total),0) as sale_amount, 
sum(ai.amount_total_signed) as invoice_amount, 
sum(apx.amount) as payment_amount, 
coalesce(sum(aipr.amount),0) as xpayment_amount, 
coalesce(sum(xaipr.amount),0) as ret_ext, coalesce(string_agg(aipr.journal,','),'') as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real, 
coalesce(string_agg(aipr.payment_document,','),'') as payment_document, 
sum(xxaipr.amount) as payment_day 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
left join (
	select aipr.invoice_id,
	sum(ap2.amount) as amount
	from account_invoice_payment_rel aipr 
	inner join account_payment ap2
	on ap2.id = aipr.payment_id and ap2.payment_date <= %s 
	group by aipr.invoice_id  
) as apx
on apx.invoice_id = ai.id 
left join ( 
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
    string_agg(ap.description_gp,',') as payment_document, 
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
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	group by aipr3.invoice_id 
) as xxaipr 
on xxaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice <= %s and ai.journal_id in %s 
group by ai.number 
having sum(apx.amount) = sum(ai.amount_total_signed) and sum(xxaipr.amount) > 0 
and count(aisor.account_invoice_id)=1 """
        params = (date_q, date_q, date_q, date_q, date_q_start, date_q, tuple(journals))
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'order': line['order'],
                'invoice': line['invoice'],
                'partner': line['partner'],
                'sale_amount': line['sale_amount'],
                'invoice_amount': line['invoice_amount'],
                'payment_amount': line['xpayment_amount'],
                'ret_ext': line['ret_ext'],
                'journal': line['journal'],
                'residual': line['invoice_amount']-line['payment_amount'],
                'date_payment': line['payment_date_real'] + '('+line['payment_date_real']+')',
            }
            invoice_day_lines.append(vals)
        query2 = """
select distinct count(aisor.account_invoice_id) as conteo, coalesce(string_agg(so.name,','),'') as order, ai.number as invoice, 
string_agg(rp.name,',') as partner, coalesce(sum(so.amount_total),0) as sale_amount,  
(sum(ai.amount_total_signed)/count(aisor.account_invoice_id)) as invoice_amount, 
(sum(apx.amount)/count(aisor.account_invoice_id)) as payment_amount, 
coalesce((sum(aipr.amount)/count(aisor.account_invoice_id)),0) as xpayment_amount, 
coalesce(sum(xaipr.amount),0) as ret_ext, coalesce(string_agg(aipr.journal,','),'') as journal, coalesce(string_agg(aipr.payment_date_real,','),'') as payment_date_real, 
coalesce(string_agg(aipr.payment_document,','),'') as payment_document, 
sum(xxaipr.amount) as payment_day 
from account_invoice ai 
inner join res_partner rp 
on rp.id = ai.partner_id 
left join (
	select aipr.invoice_id,
	sum(ap2.amount) as amount
	from account_invoice_payment_rel aipr 
	inner join account_payment ap2
	on ap2.id = aipr.payment_id and ap2.payment_date <= %s 
	group by aipr.invoice_id  
) as apx
on apx.invoice_id = ai.id 
left join ( 
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount, string_agg(aj.name,',') as journal, 
    string_agg(ap.description_gp,',') as payment_document, 
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
	select distinct aipr3.invoice_id as invoice_id, 
	sum(ap.amount) as amount 
	from account_invoice_payment_rel aipr3
	inner join account_payment ap 
	on ap.id = aipr3.payment_id and ap.payment_date = %s 
	group by aipr3.invoice_id 
) as xxaipr 
on xxaipr.invoice_id = ai.id 
inner join account_invoice_sale_order_rel aisor 
on aisor.account_invoice_id = ai.id 
inner join sale_order so 
on so.id = aisor.sale_order_id and so.confirmation_date < %s 
where ai.date_invoice <= %s and ai.journal_id in %s 
group by ai.number 
having sum(apx.amount) = sum(ai.amount_total_signed) and sum(xxaipr.amount) > 0 
and count(aisor.account_invoice_id)>1 """
        params2 = (date_q, date_q, date_q, date_q, date_q_start, date_q, tuple(journals))
        self.env.cr.execute(query2, params2)
        for line2 in self.env.cr.dictfetchall():
            vals = {
                'order': line2['order'],
                'invoice': line2['invoice'],
                'partner': line2['partner'],
                'sale_amount': line2['sale_amount'],
                'invoice_amount': line2['invoice_amount'],
                'payment_amount': line2['xpayment_amount'],
                'ret_ext': line2['ret_ext'],
                'journal': line2['journal'],
                'residual': line2['invoice_amount']-line2['payment_amount'],
                'date_payment': line2['payment_date_real'] + '('+line2['payment_date_real']+')',
            }
            invoice_day_lines.append(vals)
        return invoice_day_lines

    def journal_detail(self, date):
        detail_journal_amount = []
        journals = [x.id for x in self.journal_ids]
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
    inner join account_invoice_payment_rel aipr 
	on aipr.payment_id = ap2.id 
	inner join account_invoice ai 
	on ai.id = aipr.invoice_id 
	inner join account_journal aj2 
	on aj2.id = ai.journal_id and aj2.id in %s 
	where ap2.payment_date = %s 
	group by ap2.journal_id 
) as ap 
on aj.id = ap.journal_id 
group by aj.name, ap.amount """
        params = (tuple(journals),date_q)
        self.env.cr.execute(query, params)
        for line in self.env.cr.dictfetchall():
            vals = {
                'journal': line['journal'],
                'amount': line['amount'],
            }
            detail_journal_amount.append(vals)
        return detail_journal_amount
