import asyncio

import httpx
print ("This is main test_requests_file.py")

data_generate_questions = {"material_path" : "files/regulations_main.pdf",
                           "previous_questions" : [{"question_text" : "Вопрос1", "correct_answers"   : ["Ответ1", "Ответ2"],
                                                                                 "incorrect_answers" : ["Ответ1", "Ответ2"] },
                                                   {"question_text" : "Вопрос2", "correct_answers"   : ["Ответ1", "Ответ2"],
                                                                                 "incorrect_answers" : ["Ответ1", "Ответ2"] },
                                                   {"question_text" : "Вопрос3", "correct_answers"   : ["Ответ1", "Ответ2"],
                                                                                 "incorrect_answers" : ["Ответ1", "Ответ2"] }],
                           "questions_amt" : 3}

data_generate_chat_answer = {"request_text" : "Расскажи мне что-нибудь",
                             "material_path" : "files/regulations_main.pdf",
                             "chat_history" : [ {"role": "user", "content": "Что такое пропускной режим?"},
                                                {"role": "assistant", "content": "Когда пропускают не всех..."},
                                                {"role": "user", "content": "А кого пропускают?"} ]}

async def test_post_with_file(client, url, file_path):
    try:
        with open(file_path, "rb") as file:
            response = await client.post(f"http://localhost:8001/{url}/", files = {"file" : file})
            response.raise_for_status()
            return response.text
    except Exception as exc:
        return (f"Ошибка в {url}. {exc}")

async def test_post_with_data(client, url, data):
    try:
        response = await client.post(f"http://localhost:8001/{url}/", json = data)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        return (f"Ошибка в {url}. {exc}")

async def main():
    
    print("Starting test requests...")
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        tasks = [
                 #test_post_with_file(client,"parse_program_file", "files/DP_VZP_792-2025.docx"),
                 #test_post_with_file(client, "parse_program_file", "files/POA_s_testovymi_voprosami.docx"),
                 test_post_with_file(client, "parse_program_file", "files/POB_100-001-22_obschaya.docx")
                 #test_post_with_file(client, "parse_program_file", "files/POSIZ_100_001_23_OOO_VVSS_Programma_obuchenia_po_ispolzovaniyu_primeneniyu-1.docx"),
                 #test_post_with_data(client,"generate_questions", data_generate_questions),
                 #test_post_with_data(client,"generate_chat_answer", data_generate_chat_answer)
                 ]
        results = await asyncio.gather(*tasks)
        for result in results:
            print(result) 
            print("--------------------------------------------------")

if __name__ == "__main__":
    print("Hello, world!")  
    asyncio.run(main())