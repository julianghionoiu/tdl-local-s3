# tdl-local-s3
Standalone S3 running locally based on Minio

Download `minio` (see https://docs.minio.io/docs/minio-client-quickstart-guide)

The downloaded binary will be called `mc` - this clashes with the program `midnight command` on Linux/MacOS, hence to correctly refer to the program do the below:

```bash 
mv mc /usr/bin/minio
chmod +x /usr/bin/minio
```   

To run:
```bash
python minio-wrapper.py start

minio config host add myminio http://192.168.1.190:9000 local_test_access_key local_test_secret_key
```

To stop:
```bash
python minio-wrapper.py stop
```
