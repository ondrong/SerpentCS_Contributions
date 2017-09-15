# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import StringIO
import base64

from openerp.tools import ustr
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp import models, fields, api


@api.model
def _create_yaml(self, data):
    mod = self.env['ir.module.record']
    try:
        res_xml = mod.generate_yaml()
    except Exception, e:
        raise except_orm(_('Error'), _(str(e)))
    return {
        'yaml_file': base64.encodestring(res_xml),
    }


@api.model
def _create_module(self, cr, uid, ids, context=None):
    mod = self.env['ir.module.record']
    res_xml = mod.generate_xml()
    ids = self.search([('id', 'in', ids)])
    data = ids.read([])[0]
    s = StringIO.StringIO()
    zip_file = zipfile.ZipFile(s, 'w')
    dname = data['directory_name']
    data['update_name'] = ''
    data['demo_name'] = ''
    if ['data_kind'] == 'demo':
        data['demo_name'] = '"%(directory_name)s_data.xml"' % data
    else:
        data['update_name'] = '"%(directory_name)s_data.xml"' % data
    cr, uid, context = self.env.args
    context = dict(context)
    depends = context.get('depends')
    data['depends'] = ','.join(map(lambda x: '"' + x + '"', depends.keys()))
    _openerp = """{
        "name": "%(name)s",
        "version": "%(version)s",
        "author": "%(author)s",
        "website": "%(website)s",
        "category": "%(category)s",
        "description": \"\"\"%(description)s\"\"\",
        "depends": [%(depends)s],
        "data": [%(update_name)s],
        "demo": [%(demo_name)s],
        "installable": True} """ % data

    filewrite = {
        '__init__.py': '#\n# Generated by the OpenERP module recorder !\n#\n',
        '__openerp__.py': _openerp,
        data['directory_name'] + '_data.xml': res_xml
    }
    for name, datastr in filewrite.items():
        info = zipfile.ZipInfo(dname + '/' + name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 2175008768
        if not datastr:
            datastr = ''
        zip_file.writestr(info, datastr)
    zip_file.close()
    file_nam = data['directory_name'] + '-' + data['version'] + '.zip'
    return {
        'module_file': base64.encodestring(s.getvalue()),
        'module_filename': file_nam,
        'name': data['name'],
        'version': data['version'],
        'author': data['author'],
        'website': data['website'],
        'category': data['category'],
        'description': data['description'],
        'directory_name': data['directory_name'],
    }


class BaseModuleSave(models.TransientModel):
    _name = 'base.module.save'
    _description = "Base Module Save"

    @api.model
    def default_get(self, fields):
        mod = self.env['ir.module.record']
        result = {}
        cr, uid, context = self.env.args
        context = dict(context)
        recording_data = context.get('recording_data')
        info = "Details of " + str(len(recording_data)) + " Operation(s):\n\n"
        res = super(BaseModuleSave, self).default_get(fields)
        for line in recording_data:
            result.setdefault(line[0], {})
            result[line[0]].setdefault(line[1][3], {})
            result[line[0]][line[1][3]].setdefault(line[1][3], 0)
            result[line[0]][line[1][3]][line[1][3]] += 1
        for key1, val1 in result.items():
            info += key1 + "\n"
            for key2, val2 in val1.items():
                info += "\t" + key2 + "\n"
                for key3, val3 in val2.items():
                    info += "\t\t" + key3 + " : " + str(val3) + "\n"
        if 'info_text' in fields:
            res.update({'info_text': info})
        if 'info_status' in fields:
            info_status = mod.recording and 'record' or 'no'
            res.update({'info_status': info_status})
        return res

    info_text = fields.Text('Information', readonly=True)
    info_status = fields.Selection([('no', 'Not Recording'),
                                    ('record', 'Recording')],
                                   'Status', readonly=True)
    info_yaml = fields.Boolean('YAML')

    @api.multi
    def record_save(self):
        #  data = self.read(self._cr, self.user_id.id, ids, [])[0]
        data = self.read(self._cr, self.user_id.id, self.ids, [])[0]
        mod_obj = self.env['ir.model.data']
        cr, uid, context = self.env.args
        context = dict(context)
        recording_data = context.get('recording_data')
        if len(recording_data):
            if data['info_yaml']:
                res = _create_yaml(self, data)
                model_data_ids =\
                    mod_obj.search([('model', '=', 'ir.ui.view'),
                                    ('name', '=', 'yml_save_form_view')])
                resource_id = mod_obj.read(self._cr, self.user_id.id,
                                           model_data_ids,
                                           fields=['res_id'])[0]['res_id']
                return {
                    'name': _('Module Recording'),
                    'context': {
                        'default_yaml_file': ustr(res['yaml_file']),
                    },
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'base.module.record.objects',
                    'views': [(resource_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                model_data_ids =\
                    mod_obj.search([('model', '=', 'ir.ui.view'),
                                    ('name', '=', 'info_start_form_view')])
                resource_id = mod_obj.read(self._cr, self.user_id.id,
                                           model_data_ids,
                                           fields=['res_id'])[0]['res_id']
                return {
                    'name': _('Module Recording'),
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'base.module.record.objects',
                    'views': [(resource_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
        model_data_ids =\
            mod_obj.search([('model', '=', 'ir.ui.view'),
                            ('name', '=', 'module_recording_message_view')])
        resource_id = mod_obj.read(model_data_ids,
                                   fields=['res_id'])[0]['res_id']
        return {
            'name': _('Module Recording'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.module.record.objects',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
