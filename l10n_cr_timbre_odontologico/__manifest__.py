{
    'name': 'Timbre Odontologico',
    'version': '1.0',
    'description': 'Timbre Odontologico',
    'summary': 'Timbre Odontologico',
    'author': 'MyCompany',    
    'license': 'LGPL-3',
    'category': '',
    'depends': [
        'cr_electronic_invoice','account'
    ],
    'data': [
        'data/partner_timbre.xml',
        'data/mail_template_data.xml',
        'views/res_company.xml',
        'views/account_move.xml',
        'reports/account_move.xml',
    ],
}