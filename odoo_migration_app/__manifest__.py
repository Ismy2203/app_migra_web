{
    'name': 'Odoo Migration App',
    'version': '1.0',
    'sequence': -1003,
    'category': 'Tools',
    'summary': 'App to manage data migrations between Odoo versions',
    'description': """
    This module allows the migration of data between different Odoo versions,
    supporting model and field mapping, error handling, and testing.
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'depends': ['base'],
    'data': [
        'views/migration_form.xml',
        'views/migration_test_view.xml',
        'views/migration_log_view.xml',
        'data/migration_sample_data.xml',
        'security/ir.model.access.csv', 
    ],
    'installable': True,
    'application': True,
}
