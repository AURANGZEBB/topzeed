from odoo.tools import safe_eval
from ast import literal_eval

from odoo import models, fields, api,_
from odoo.exceptions import UserError

from odoo.tools import config
from odoo.tools import format_datetime

from odoo.tools.misc import xlwt
import io
import base64
import json
from odoo.tools import html2plaintext, html_escape

class AccountHierarchy(models.TransientModel):
    _name = "account.hierarchy"
    _description = "Account Hiearchy"

    @api.model
    def get_company_domain_ids(self):
        company_ids = self.env.user.company_ids.ids
        return "[('id', 'in', %s)]" % (company_ids)
    
    date_from = fields.Date(string='Start Date', required=False)
    date_to = fields.Date(string='End Date', required=False)
    target_moves = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
        ], string='Target Moves', required=True, default='posted')
    company_id = fields.Many2one('res.company', string='Company', domain=get_company_domain_ids, required=True, default=lambda self: self.env.user.company_id)
    auto_unfold = fields.Boolean(string='Auto Unfold')
    
    @api.onchange('date_to','date_from')
    def onchange_date(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise UserError(_('End date must be greater than start date.'))
    
    def print_pdf_report_wizard(self):
        context = dict(self.env.context)
        active_id = context.get('active_id') or self.id    
        report_lines = self.with_context(print_mode=True).get_report_lines(active_id)
        active_context = {       
            'active_id': self.id,     
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'state' : self.target_moves,
            'company_id': self.company_id.id,
            'auto_unfold' : self.auto_unfold,
        }
        self = self.with_context(active_context)
        company_name = self.env['res.company'].browse(self.browse(active_id).company_id.id).display_name        
        datas = {
            'ids': self.ids,
            'company_name' : company_name,
            'model': self._name,
            'lines' : report_lines,
        }
        return self.env.ref('odoo_account_hierarchy.action_account_hierarchy_report').report_action(self, data=datas)
    
    def print_pdf_report(self):
        context = dict(self.env.context)        
        ir_actions_report_env = self.env['ir.actions.report']
        active_id = context.get('active_id') or self.id    
        report_lines = self.with_context(print_mode=True).get_report_lines(active_id)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        company_name = self.env['res.company'].browse(self.browse(active_id).company_id.id).display_name
        rcontext = {
            'mode': 'print',
            'base_url': base_url,           
        }
        rcontext['reference'] = self.env['account.hierarchy'].browse(int(context.get('active_id'))).display_name
        body = self.env['ir.ui.view'].with_context(context)._render_template(
            "odoo_account_hierarchy.report_account_hierarchy",
            values=dict(
                rcontext,
                company_name=company_name,
                lines=report_lines,
                report=self,
                context=self
            ),
        )    
        return ir_actions_report_env._run_wkhtmltopdf(
            [body],
            landscape=True,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )
    
    @api.model
    def get_report_lines(self, active_id):
        report_lines = self.browse(active_id).get_report_all_lines()
        return report_lines

    @api.model
    def get_report_all_lines(self, line_id=False, level=1):
        self.ensure_one()
        result = []
        for report_line in self.get_lines(self.id, line_id=line_id, level=level):
            result.append(report_line)
            result.extend(self.get_report_all_lines(line_id=report_line['rec_id'], level=report_line['level']+1))
        return result
    
    def print_xls_report(self, response=None):
        context = dict(self.env.context)
        active_id = context.get('active_id') or self.id
        report_lines = self.with_context(print_mode=True).get_report_lines(active_id)
        company_name = self.env['res.company'].browse(self.browse(active_id).company_id.id).display_name
        if report_lines:
            if len(report_lines) > 65535:
                raise UserError(_('There are too many rows (%s rows, limit: 65535) to export as Excel 97-2003 (.xls) format.') % len(report_lines))
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet('Chart of Account')

            r_normal = xlwt.easyxf('font: name Times New Roman ;align: horiz left;', num_format_str='#,##0.00')            
            r_bold = xlwt.easyxf('font: name Times New Roman bold ;align: horiz left;', num_format_str='#,##0.00')
            r_head = xlwt.easyxf('font: name Times New Roman bold ;align: horiz centre, vert centre;', num_format_str='#,##0.00')
            if company_name:
                sheet.write_merge(0, 1, 0,5, 'Chart of Account Hierarchy for ' + company_name + '', r_bold)
            else:
                sheet.write_merge(0, 1, 0,5, 'Chart of Account Hierarchy', r_head)

            sheet.write(3, 0,'Code', r_bold)
            sheet.write(3, 1,'Name', r_bold)
            sheet.write(3, 2,'Type', r_bold)
            sheet.write(3, 3,'Debit', r_bold)
            sheet.write(3, 4,'Credit', r_bold)
            sheet.write(3, 5,'Balance', r_bold)

            i = 4
            for line in report_lines:
                sheet.write(i, 0, line['line_columns'][0] or '', r_normal)
                sheet.write(i, 1, line['line_columns'][1] or '', r_normal)
                sheet.write(i, 2, line['line_columns'][2] or '', r_normal)
                sheet.write(i, 3, html2plaintext(line['line_columns'][3]) or '0', r_normal)
                sheet.write(i, 4, html2plaintext(line['line_columns'][4]) or '0', r_normal)
                sheet.write(i, 5, html2plaintext(line['line_columns'][5]) or '0', r_normal)            
                i += 1  
            
            if response:
                fp = io.BytesIO()
                workbook.save(fp)
                fp.seek(0)
                response.stream.write(fp.read())
                fp.close()
            else:            
                filename = ('Account_Hiearchy'+ '.xls')
                fp = io.BytesIO()
                workbook.save(fp)                    
                export_id = self.env['report.account.hierarchy.excel'].sudo().create({
                    'report': base64.encodestring(fp.getvalue()), 
                    'file_name': filename,
                    })                
                return{
                    'type' : 'ir.actions.act_url',
                    'url':'web/content/?model=report.account.hierarchy.excel&field=report&download=true&id=%s&filename=%s'%(export_id.id,filename),
                    'target': 'new',
                }
            
    def open_account_hierarchy(self):
        self.ensure_one()
        result = {}
        account_env = self.env['account.account']
        active_context = {       
            'active_id': self.id,     
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'state' : self.target_moves,
            'company_id': self.company_id.id,
            'auto_unfold' : self.auto_unfold,
        }
        self  = self.with_context(active_context)
        if account_env.search([('parent_id','!=',False)],limit=1):
            result = self.env.ref('odoo_account_hierarchy.account_hierarchy_action_tag').read([])[0]
        else:           
            result = self.env.ref('account.action_account_form').read([])[0]
        rcontext = literal_eval(result.get('context',"{}")) or {}
        rcontext.update(active_context)
        result['context'] = rcontext
        return result
    
    @api.model
    def get_html(self, given_context=None):
        res = self
        return res.with_context(given_context)._get_html()
    
    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        active_id = context.get('active_id')
        company_id = context.get('company_id')
        active_model = context.get('active_model')
        if active_model == 'account.hierarchy' and  company_id and active_id:
            rcontext['lines'] = self.with_context(context).get_lines(active_id)
            rcontext['company_name'] = self.env['res.company'].browse(company_id).display_name
        result['html'] = self.env.ref('odoo_account_hierarchy.accounts_heirarchy_report')._render(rcontext)
        return result
    
    @api.model
    def get_lines(self, active_id=None, line_id=None, **kw):
        res = []
        account_env = self.env['account.account']
        context = dict(self.env.context)
        if active_id:
            context.update({
                'active_id' : self.browse(active_id).id,                                
                'date_from' : str(self.browse(active_id).date_from) or False,
                'date_to' : str(self.browse(active_id).date_to)  or False,
                'state' : self.browse(active_id).target_moves or '',
                'company_id' : self.browse(active_id).company_id.id,
            })
            
        rec_id = False
        level = 1
        if kw:
            level = kw.get('level', 0)
            rec_id = kw.get('rec_id')
                                
        domain = [('parent_id','=',line_id),('company_id','=',context.get('company_id',False))]
        lines = account_env.with_context(context).search(domain)
        line_vals = self._lines(active_id, line_id, rec_id=rec_id, level=level, lines=lines)
        
        final_vals = sorted(line_vals, key=lambda v: v['code'], reverse=False)
        lines = self._final_values_to_lines(final_vals, level)
        return lines
    
    @api.model
    def _lines(self, active_id=None, line_id=None, rec_id=False, level=0, lines=[], **kw):
        final_vals = []
        lines = lines or []
        context = dict(self.env.context)
        unfoldable = False
        for line in lines:
            unfoldable = False
            final_vals += self._make_line_dict(level = level, active_id = active_id, parent_id=line_id, line=line, unfoldable=False)        
        return final_vals
    
    def _make_line_dict(self, level, active_id, parent_id, line, unfoldable=False):        
        context = dict(self.env.context)
        if active_id:
            context.update({
                'date_from' : str(self.browse(active_id).date_from) or False,
                'date_to' : str(self.browse(active_id).date_to)  or False,
                'state' : self.browse(active_id).target_moves or '',
                'company_id' : self.browse(active_id).company_id.id,
                'active_id' : self.browse(active_id).id,
            })
        line.with_context(context).get_account_hierarchy_lines()
        line_data = [{
            'id': line.id,
            'level': level,
            'rec_id': line.id,
            'parent_id': parent_id,                                                
            'code': line.code,
            'name': line.name,
            'type': line.user_type_id.name,
            'debit': self._amount_to_string(line.debit, line.company_id.currency_id),
            'credit': self._amount_to_string(line.credit, line.company_id.currency_id),
            'balance': self._amount_to_string(line.balance, line.company_id.currency_id),
            'active_id': active_id,
            'unfoldable': line.has_child and True or False,
        }]
        return line_data

    @api.model
    def _amount_to_string(self, value, currency):
        return self.env['ir.qweb.field.monetary'].value_to_html(value, {'display_currency': currency})
                
    @api.model
    def _final_values_to_lines(self, final_vals, level):
        lines = []
        for data in final_vals:
            lines.append({
                'id': data['id'],
                'level': level,
                'active_id': data['active_id'],
                'rec_id': data['rec_id'],
                'parent_id': data['parent_id'],
                'type': data.get('type'),
                'name': _(data.get('name')),
                'line_columns': [                    
                    data.get('name'),
                    data.get('code'),
                    data.get('type'),
                    data.get('debit'),
                    data.get('credit'),
                    data.get('balance'),
                ],             
                'unfoldable': data['unfoldable'],
            })
        return lines
    
    @api.model
    def get_child_ids(self, active_id=None, line_id=None):
        lines = []
        account_env = self.env['account.account']
        context = dict(self.env.context)
        if active_id:
            context.update({
                'date_from' : str(self.browse(active_id).date_from) or False,
                'date_to' : str(self.browse(active_id).date_to)  or False,
                'state' : self.browse(active_id).target_moves or '',
                'company_id' : self.browse(active_id).company_id.id,
                'active_id' : self.browse(active_id).id,
            })
        if active_id and line_id:
            child_of_ids = account_env.sudo().search([('id','child_of',[line_id])]).ids
            lines.append(('account_id','child_of',child_of_ids))            
            
            if context['date_from'] != 'False':
                lines.append(('date', '>=', context['date_from']))
            if context['date_to'] != 'False':
                lines.append(('date', '<=', context['date_to']))   

            if context['state'] == 'posted':
                lines.append(('move_id.state', '=', 'posted'))
            else:
                lines.append(('move_id.state', 'in', ['posted','draft']))
                                
        return lines                        
    
    
class ReportAccountHierarchyExcel(models.TransientModel):
    _name = "report.account.hierarchy.excel"
        
    file_name = fields.Char('File Name', size=256 ,readonly=True)
    report = fields.Binary('Excel report', readonly=True)