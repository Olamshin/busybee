import PyInstaller.__main__


PyInstaller.__main__.run([
    'busybee/__main__.py',
    '--onefile',
    '--name=busybee',
    '--add-data=config.yml:.',
    '--noconfirm'
])
