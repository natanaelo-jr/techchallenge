import asyncio
import base64
from src.scraper.browser import BrowserManager
from src.services.telegram_captcha import TelegramCaptchaManager, CaptchaBypassError


async def scrollAndClick(element) -> None:
    await element.hover()
    await element.click(force=True)


async def search(page, searchString: str) -> None:
    # Filtra a busca por beneficiário de programa social
    filterAcc = page.locator("text=REFINE A BUSCA").locator("..")
    chevDown = filterAcc.locator("..")
    for _ in range(5):
        isActive = await chevDown.get_attribute("active")
        if isActive is not None:
            break
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")

    checkBox = page.locator("#beneficiarioProgramaSocial").locator("..")
    await scrollAndClick(checkBox)

    # Realiza a busca
    searchInput = page.locator("#termo")
    await searchInput.fill(searchString)
    await searchInput.press("Enter")
    return


async def backToBenefitPage(page):
    # Volta pra página anterior e reabre a lista de beneficios
    await page.go_back()
    await page.wait_for_load_state("domcontentloaded")
    filterAcc = page.locator("text=RECEBIMENTOS DE RECURSOS").locator("..")
    chevDown = filterAcc.locator("..")
    for _ in range(5):
        isActive = await chevDown.get_attribute("active")
        if isActive is not None:
            return
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")
    raise TimeoutError("Não foi possível abrir um dos componentes.")


async def getBenefitTable(benefit_item, page, captcha_manager, manager) -> list:
    # Inicializa a resposta do possível captcha como nula

    captcha_response = None
    # Lock aqui para que cada agente só clique no botão de detalhar isoladamente, para evitar multiplos captchas
    async with manager.detailsLock:
        goToDetailsBtn = benefit_item.locator("a").first
        await scrollAndClick(goToDetailsBtn)

        title = await page.title()

        if title == "Human Verification":
            begin_button = page.locator(".amzn-captcha-verify-button")
            await scrollAndClick(begin_button)

            await asyncio.sleep(0.5)

            captcha_div = page.locator("#root").first
            captcha_screenshot = await captcha_div.screenshot()

            # Timeout no evento e tratar caso não haja resposta a tempo
            try:
                captcha_response = await asyncio.wait_for(
                    captcha_manager.send_captcha_and_wait(captcha_screenshot),
                    timeout=30,
                )
            except (asyncio.TimeoutError, Exception) as e:
                await backToBenefitPage(page)
                # Lançamos o erro para ser capturado no loop do parsePage
                raise CaptchaBypassError(f"Detalhes omitidos: {str(e)}")

            canvas = page.locator("canvas").first

            for char in captcha_response:
                if char.isdigit() and 1 <= int(char) <= 9:
                    index = int(char) - 1
                    col = index % 3
                    row = index // 3

                    x = (col + 0.5) * (320 / 3)
                    y = (row + 0.5) * (320 / 3)

                    await canvas.click(position={"x": x, "y": y})
                    await asyncio.sleep(0.4)

            verify_button = page.locator("#amzn-btn-verify-internal")
            await verify_button.click()
            await page.wait_for_load_state("networkidle")

    # Testar se o captcha foi resolvido aqui
    title = await page.title()
    if title == "Human Verification":
        await backToBenefitPage(page)
        return ["O Captcha não foi resolvido a tempo"]

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
    await backToBenefitPage(page)
    return benefit_table


async def getText(page, label_text, timeout=5000):
    try:
        locator = (
            page.locator(f"strong:has-text('{label_text}')")
            .locator("..")
            .locator("span")
        )
        await locator.wait_for(state="visible", timeout=timeout)
        return await locator.inner_text()
    except:
        raise


async def parsePage(page, captcha_manager, browserManager) -> dict:
    # Abre a aba de recebimento
    filterAcc = page.locator("text=RECEBIMENTOS DE RECURSOS").locator("..")
    chevDown = filterAcc.locator("..")
    isActive = await chevDown.get_attribute("active")
    while isActive is None:
        await scrollAndClick(filterAcc)
        isActive = await chevDown.get_attribute("active")

    # Tira o print da janela
    screenshot_bytes = await page.screenshot()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    # Parse data
    # Nome
    textName = await getText(page, "Nome")

    # CPF
    textCPF = await getText(page, "CPF")

    # Local
    textLocal = await getText(page, "Localidade")

    # Tipo do auxilio
    table = page.locator(".br-table")
    n_elements = await table.count()
    benefits = []
    for i in range(n_elements):
        try:
            table_item = table.nth(i)

            auxType = await table_item.locator("strong").first.inner_text()

            amount = table_item.locator("text=R$").first
            amountText = await amount.inner_text()
            parsedAmount = amountText.replace(".", "").replace(",", ".")

            bf_table = await getBenefitTable(
                table_item, page, captcha_manager, browserManager
            )

            benefits.append(
                {
                    "name": auxType,
                    "totalAmount": parsedAmount,
                    "details": bf_table,
                    "status": "sucesso",
                }
            )
        except CaptchaBypassError as e:
            # Se o captcha falhou, salvamos o benefício com um aviso nos detalhes
            benefits.append(
                {
                    "name": auxType,
                    "totalAmount": parsedAmount,
                    "details": [],
                    "status": f"erro_captcha: {str(e)}",
                }
            )
            continue

        except Exception as e:
            # Erro genérico em um item da lista não deve travar os outros
            print(f"Erro inesperado no item {i}: {e}")
            continue

    data = {
        "success": True,
        "name": textName,
        "CPF": textCPF,
        "location": textLocal,
        "benefits": benefits,
    }

    data["screenshot"] = screenshot_b64
    return data


async def scrape(browser, captcha_manager, searchString: str) -> dict:
    page = None
    async with browser.semaphore:
        try:
            # Se faltar query retorna erro e avisa
            if not searchString or searchString == "":
                raise ValueError("Parâmetro de busca ausente")

            # Cria a página
            page = await browser.newPage()

            # Poderia ir direto para https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista porem especificação nao deixa claro
            await page.goto(
                "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"
            )
            await asyncio.wait_for(
                page.wait_for_load_state("domcontentloaded"), timeout=5
            )

            # Caminha na pagina e realiza a busca
            await search(page, searchString)

            # Extrai o número de resultados encontrados
            countResults = page.locator("#countResultados")
            await countResults.wait_for(state="visible", timeout=15000)

            numberOfResults = await countResults.inner_text()

            # Pega o primeiro resultado se ele existe
            if numberOfResults == "0":
                # Retornar o json formatado para deixar a mensagem correta.
                if searchString.isnumeric():
                    data = {
                        "success": False,
                        "results": "Não foi possível retornar os dados no tempo de resposta solicitado",
                    }
                else:
                    data = {
                        "success": False,
                        "results": f"Foram encontrados 0 resultados para o termo {searchString}",
                    }
                await page.close()
                return data

            result = page.locator(".link-busca-nome").first
            await scrollAndClick(result)

            data = await parsePage(page, captcha_manager, browser)
            await page.close()
            return data
        except Exception as e:
            print(f"Erro durante o scraping: {str(e)}")
            if page:
                await page.screenshot(path="error_screenshot.png")
            raise
        finally:
            if page:
                await page.close()


async def main() -> None:
    browser = BrowserManager()
    await browser.start(headless=False)
    captcha_manager = TelegramCaptchaManager()
    test_call_result = await scrape(browser, captcha_manager, "Maria")
    print(test_call_result)


if __name__ == "__main__":
    asyncio.run(main())
