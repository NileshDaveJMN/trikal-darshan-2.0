from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0013_pushsubscription'),
    ]
    operations = [
        migrations.AlterField(
            model_name='learnitem',
            name='pdf_file',
            field=models.URLField(blank=True, null=True, verbose_name='PDF Google Drive Link'),
        ),
    ]
