{
    'name': 'Invoice Picking',
    'version': '1.0',
    'description': 'Invoice Picking',
    'summary': 'Invoice Picking',
    'author': 'MyCompany',    
    'license': 'LGPL-3',
    'category': '',
    'depends': [
        'cr_electronic_invoice','account'
    ],
    'data': [
        'views/account_move.xml',
        'views/stock_picking_type.xml',
    ],
}