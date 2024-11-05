document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('button');
    
    if (buttons) {
        buttons.forEach(button => {
            button.addEventListener('mouseover', () => {
                button.style.transition = 'transform 0.2s';
                button.style.transform = 'scale(1.05)';
            });

            button.addEventListener('mouseout', () => {
                button.style.transform = 'scale(1)';
            });

            button.addEventListener('click', () => {
                button.style.transition = 'transform 0.1s';
                button.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    button.style.transform = 'scale(1)';
                }, 100);
            });
        });
    }

    // Animação para botões de envio
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', (event) => {
            event.preventDefault();
            submitBtn.innerHTML = 'Enviando...';
            submitBtn.disabled = true;

            const distinctMessage = document.createElement('div');
            distinctMessage.innerHTML = 'Documento criado e enviado para aprovação!';
            setMessageStyle(distinctMessage, '#2196F3');

            document.body.appendChild(distinctMessage);

            setTimeout(() => {
                distinctMessage.remove();
                submitBtn.innerHTML = 'Enviar para Aprovação';
                submitBtn.disabled = false;
                document.getElementById('document-form').submit();
            }, 3000);
        });
    }

    // Animação para botões de cancelamento
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (event) => {
            event.preventDefault();
            cancelBtn.innerHTML = 'Enviando...';
            cancelBtn.disabled = true;

            const cancelMessage = document.createElement('div');
            cancelMessage.innerHTML = 'Solicitação de cancelamento enviada!';
            setMessageStyle(cancelMessage, '#FF5722');

            document.body.appendChild(cancelMessage);

            setTimeout(() => {
                cancelMessage.remove();
                cancelBtn.innerHTML = 'Cancelar Documento';
                cancelBtn.disabled = false;
                document.getElementById('cancel-document-form').submit();
            }, 3000);
        });
    }

    // Animação para botões de revisão
    const reviewBtn = document.getElementById('review-btn');
    if (reviewBtn) {
        reviewBtn.addEventListener('click', (event) => {
            event.preventDefault();
            reviewBtn.innerHTML = 'Enviando...';
            reviewBtn.disabled = true;

            const reviewMessage = document.createElement('div');
            reviewMessage.innerHTML = 'Documento enviado para revisão!';
            setMessageStyle(reviewMessage, '#FFC107');

            document.body.appendChild(reviewMessage);

            setTimeout(() => {
                reviewMessage.remove();
                reviewBtn.innerHTML = 'Revisar Documento';
                reviewBtn.disabled = false;
                document.getElementById('review-document-form').submit();
            }, 3000);
        });
    }

    // Função para mostrar mensagem de sucesso
    function setMessageStyle(messageElement, bgColor) {
        messageElement.style.position = 'fixed';
        messageElement.style.top = '50%';
        messageElement.style.left = '50%';
        messageElement.style.transform = 'translate(-50%, -50%)';
        messageElement.style.backgroundColor = bgColor;
        messageElement.style.color = 'white';
        messageElement.style.padding = '20px';
        messageElement.style.borderRadius = '5px';
        messageElement.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';
    }

    // Funções para ver e resumir PDF
    const app = {
        viewPdf: function (url) {
            const pdfViewer = document.getElementById('app-pdf-viewer');
            if (pdfViewer) {
                pdfViewer.querySelector('iframe').src = url;
                pdfViewer.querySelector('h2').innerText = 'Visualizando PDF';
            }
        },
        summarizePdf: function (docId) {
            console.log("Summarizing PDF with docId:", docId);
            fetch(`/summarize_pdf/${docId}`)
                .then(response => response.json())
                .then(data => {
                    const pdfViewer = document.getElementById('app-pdf-viewer');
                    if (pdfViewer) {
                        pdfViewer.querySelector('p').innerText = data.summary || 'Erro ao resumir o PDF.';
                    }
                })
                .catch(() => {
                    const pdfViewer = document.getElementById('app-pdf-viewer');
                    if (pdfViewer) {
                        pdfViewer.querySelector('p').innerText = 'Erro ao se conectar com o servidor.';
                    }
                });
        }
    };

    // Adiciona `app` ao escopo global
    window.app = app;
});
