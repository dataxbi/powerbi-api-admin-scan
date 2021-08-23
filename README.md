# powerbi-api-admin-scan

Un script Python para demostrar el uso de la Scanner API de Power BI 
https://powerbi.microsoft.com/es-es/blog/scanner-api-is-now-in-ga/


Puede encontrar más información sobre este script en esta entrada de blog: https://www.dataxbi.com/blog/2021/08/23/probando-scanner-api-power-bi/


Requerimientos:
- Habilitar la autenticación por entidad de servicio 
  https://docs.microsoft.com/es-es/power-bi/admin/read-only-apis-service-principal-authentication
- Configurar el inquilino de Power BI para la exploración de metadata
  https://docs.microsoft.com/es-es/power-bi/admin/service-admin-metadata-scanning-setup#enable-tenant-settings-for-metadata-scanning
 

Utiliza las siguientes variables del entorno:
- PBI_TENANT_NAME: Nombre del inquilino de Power BI
- PBI_ADMIN_API_CLIENT_ID : ID de la aplicación registrada en Azure AD al configurar la autenticación por entidad de servicio
- PBI_ADMIN_API_SECRET: Secreto de cliente (o contraseña) de la aplicación registrada en Azure AD 

Al ejecutar el script, se creará una carpeta con el nombre del inquilino de Power BI, y dentro de ella se crearán varios ficheros:
- <nombre_inquilino>.json: Un solo fichero con toda la información devuelta por la Scanner API
- <nombre_area_trabajo>.json: Un fichero por cada área de trabajo
- <nombre_inquilino>_worspaces.csv: Datos generales de todas las áreas de trabajo
- <nombre_inquilino>_reports.csv: Datos de todos los informes de todas las áreas de trabajo, incluyendo el ID y el nombre del área de trabajo a la que pertenece cada informe
- <nombre_inquilino>_dashboards.csv: Datos de todos los cuadros de mando de todas las áreas de trabajo, incluyendo el ID y el nombre del área de trabajo a la que pertenece cada cuadro de mando
- <nombre_inquilino>_datasets.csv: Datos de todos los conjuntos de datos de todas las áreas de trabajo, incluyendo el ID y el nombre del área de trabajo a la que pertenece cada conjunto de datos
- <nombre_inquilino>_dataflows.csv: Datos de todos los flujos de datos de todas las áreas de trabajo, incluyendo el ID y el nombre del área de trabajo a la que pertenece cada flujo de dato











