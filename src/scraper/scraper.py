import asyncio
import base64
from browser import BrowserManager


async def scrollAndClick(element) -> None:
    await element.scroll_into_view_if_needed()
    await element.hover()
    await asyncio.sleep(0.2)
    await element.click()


async def search(page, searchString: str) -> None:
    # Acha e clica no botao pessoa fisica e juridica (clica na div pai pois o botao ta hidden)
    button = page.locator("#btnPessoa").locator("xpath=..")
    await scrollAndClick(button)

    # Acha e clica no botao Busca de pessoa fisica
    button = page.locator("#button-consulta-pessoa-fisica")
    await scrollAndClick(button)

    # Filtra a busca por beneficiário de programa social
    filterAcc = page.locator("text=REFINE A BUSCA").locator("xpath=..")
    chevDown = filterAcc.locator("xpath=..")
    isActive = await chevDown.get_attribute("active")
    while isActive is None:
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")

    checkBox = page.locator("#beneficiarioProgramaSocial").locator("xpath=..")
    await scrollAndClick(checkBox)

    # Realiza a busca
    searchInput = page.locator("#termo")
    await searchInput.fill(searchString)
    await searchInput.press("Enter")
    return


async def getBenefitTable(benefit_item, page) -> list:
    goToDetailsBtn = benefit_item.locator("#btnDetalharBpc")
    await scrollAndClick(goToDetailsBtn)

    # Pega as colunas do beneficio
    head = page.locator("thead").locator("tr").first
    hcols = head.locator("th")
    await hcols.first.wait_for(state="visible", timeout=5000)
    numberOfCols = await hcols.count()
    headcols = []
    for i in range(numberOfCols):
        column = hcols.nth(i)
        text = await column.inner_text()
        headcols.append(text)

    table = page.locator("tbody")
    rows = table.locator("tr")
    await rows.first.wait_for(state="visible", timeout=5000)
    n_rows = await rows.count()

    # Associa os elementos as respectivas colunas e salva na lista
    benefit_table = []
    for i in range(n_rows):
        row = rows.nth(i)
        row_data = {}
        rowColumns = row.locator("td")
        for j in range(numberOfCols):
            column = rowColumns.nth(j)
            span = column.locator("span")
            text = await span.inner_text()
            row_data[headcols[j]] = text
        benefit_table.append(row_data)

    # Volta pra página anterior e reabre a lista de beneficios
    await page.go_back()
    filterAcc = page.locator("text=RECEBIMENTOS DE RECURSOS").locator("xpath=..")
    chevDown = filterAcc.locator("xpath=..")
    isActive = await chevDown.get_attribute("active")
    while isActive is None:
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")

    return benefit_table


async def parsePage(page) -> dict:
    # Abre a aba de recebimento
    filterAcc = page.locator("text=RECEBIMENTOS DE RECURSOS").locator("xpath=..")
    chevDown = filterAcc.locator("xpath=..")
    isActive = await chevDown.get_attribute("active")
    while isActive is None:
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")

    # Tira o print da janela
    screenshot_bytes = await page.screenshot()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    # Parse data
    # Nome
    divName = page.locator("strong:has-text('Nome')").locator("xpath=..").first
    spanName = divName.locator("span")
    textName = await spanName.inner_text()

    # CPF
    divCPF = page.locator("strong:has-text('CPF')").locator("xpath=..").first
    spanCPF = divCPF.locator("span")
    textCPF = await spanCPF.inner_text()

    # Local
    divLocal = page.locator("strong:has-text('Localidade')").locator("xpath=..").first
    spanLocal = divLocal.locator("span")
    textLocal = await spanLocal.inner_text()

    # Tipo do auxilio
    table = page.locator(".br-table")
    n_elements = await table.count()
    benefits = []
    for i in range(n_elements):
        table_item = table.nth(i)

        auxType = await table_item.locator("strong").first.inner_text()

        amount = table_item.locator("text=R$").first
        amountText = await amount.inner_text()
        parsedAmount = amountText.replace(".", "").replace(",", ".")

        bf_table = await getBenefitTable(table_item, page)

        benefits.append(
            {"name": auxType, "totalAmount": parsedAmount, "details": bf_table}
        )

    data = {
        "name": textName,
        "CPF": textCPF,
        "location": textLocal,
        "benefits": benefits,
    }

    data["screenshot"] = screenshot_b64
    return data


async def scrape(browser, searchString: str) -> dict:
    # Abrindo o browser

    page = await browser.newPage()

    # Poderia ir direto para https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista porem especificação nao deixa claro
    await page.goto("https://portaldatransparencia.gov.br/")

    # Caminha na pagina e realiza a busca
    await search(page, searchString)

    # Extrai o número de resultados encontrados
    countResults = page.locator("#countResultados")
    try:
        await countResults.wait_for(state="visible", timeout=15000)
    except TimeoutError:
        # Timeout
        print("Timeout: Results count did not appear.")
        return {
            "sucess": False,
            "error": "Response time exceeded. Website may be unstable.",
        }
    except Exception as e:
        # Qualquer outro error
        print(f"Unexpected error: {e}")
        return {"sucess": False, "error": "Unexpected error."}

    numberOfResults = await countResults.inner_text()

    # Pega o primeiro resultado se ele existe
    if numberOfResults == "0":
        # Retornar o json formatado para deixar a mensagem correta.
        if searchString.isnumeric():
            data = {
                "error": "Não foi possível retornar os dados no tempo de resposta solicitado"
            }
        else:
            data = {
                "error": f"Foram encontrados 0 resultados para o termo {searchString}"
            }
        return data

    result = page.locator(".link-busca-nome").first
    await scrollAndClick(result)

    data = await parsePage(page)
    await page.close()
    return data


async def main() -> None:
    browser = BrowserManager()
    await browser.start()
    test_call_result = await scrape(browser, "Maria")
    print(test_call_result)


if __name__ == "__main__":
    asyncio.run(main())
