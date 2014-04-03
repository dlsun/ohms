import os
os.system('make local-deploy')

from ohms import app
app.run(debug=True)
