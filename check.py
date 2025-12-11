import google.generativeai as genai

genai.configure(api_key='AIzaSyDWknbmO00nbpzyy4A_ju5kDIjl626fPgU')

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)