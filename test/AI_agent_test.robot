*** Settings ***
Library           RPA.Excel.Files
Library           Collections
Library           OperatingSystem
Library           BuiltIn
Library           ../AutoAUTOSARAgent.py    WITH NAME    AutoAgent

*** Variables ***
${PDF_FOLDER}     ./pdf_docs
${OUTPUT_JSON}    ./test/results.json
${EXCEL_FILE}     ./test/questions.xlsx

*** Test Cases ***
Generate Knowledge Base From PDFs
    [Documentation]    Run AutoAUTOSARAgent to generate knowledge base JSON
    ${agent}=    Evaluate    AutoAUTOSARAgent("${PDF_FOLDER}", "${OUTPUT_JSON}")    modules=AutoAUTOSARAgent
    ${output}=   Run Keyword And Return    ${agent.update_knowledge_base}
    Log    Knowledge base saved at ${OUTPUT_JSON}

Verify AI Answers Against Expected
    [Documentation]    Compare answers from JSON KB against Excel expected answers
    Open Workbook    ${EXCEL_FILE}
    ${rows}=    Read Worksheet As Table    header=True
    ${results}=    Create List
    ${kb}=    Evaluate    json.load(open("${OUTPUT_JSON}"))    json
    FOR    ${row}    IN    @{rows}
        ${question}=    Set Variable    ${row['Question']}
        ${expected}=    Set Variable    ${row['Expected Answer']}
        ${module}    ${param}=    Evaluate    ${question}.split(" ")    # split module and param
        ${actual}=    Get From Dictionary    ${kb['${module}']}    ${param}
        ${pass}=    Run Keyword And Return Status    Should Be Equal    ${actual['value']}    ${expected}
        Append To List    ${results}    ${pass}
    END
    ${passed}=    Get Count    ${results}    value=True
    ${total}=     Get Length   ${results}
    ${accuracy}=  Evaluate    ${passed}*100/${total}
    Log    Accuracy: ${accuracy}%
    Close Workbook

