# Recognition via gRPC (++)

# Generate gRPC classes
```
python3 -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/RecognizeService.proto
```

# Run 
```
python3 recognize.py -f audios/audio_8k_pizza_mensagem_calendario_cpqd.wav -c true -a true
```
