import PyInstaller.__main__


PyInstaller.__main__.run([
    'src/cli.py',  # Replace with the name of your Python script
    '--name=busybee',   # Set the desired name of the executable
    '--add-data=config.yml:.',
    '--noconfirm'
])
