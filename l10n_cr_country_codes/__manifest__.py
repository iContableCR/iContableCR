{
    'name': 'Códigos País para Facturación electrónica Costa Rica',
    'version': '15.0.1.0.0',
    'author': 'Odoo CR',
    'license': 'AGPL-3',
    'website': 'https://github.com/odoocr',
    'category': 'Account',
    'description': '''Códigos País para Facturación electrónica Costa Rica.''',
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        'data/res_country_state.xml',
        'data/res.country.county.csv',
        #'data/res.country.district.csv',
        #'data/res.country.neighborhood.csv',
        'security/ir.model.access.csv',
        'views/res_country_county_views.xml',
        'views/res_country_district_views.xml',
        'views/res_country_neighborhood_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    # "pre_init_hook": "pre_init_hook",
    'installable': True,
}
