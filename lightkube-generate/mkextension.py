from markdown.inlinepatterns import InlineProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree


class ModelLinkProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        code = etree.Element("code")
        el = etree.Element("a")
        code.append(el)

        el.text = classe = m.group(1)
        if classe.startswith("List["):
            classe = classe[5:-1]
        if "." in classe:
            module, classe = classe.split(".")
            href = f"../{module}/index.html#{classe.lower()}"
        else:
            href = f"#{classe.lower()}"

        el.set("href", href)

        return code, m.start(1)-1, m.end(1)+1


class ModelLinkExtension(Extension):
    def extendMarkdown(self, md):
        PATTERN = r'\*\* `((.*?[.])?[A-Z].*?)` -'
        mp = ModelLinkProcessor(PATTERN, md)
        md.inlinePatterns.register(mp, 'class-link', 200)
        md.registeredExtensions.append(ModelLinkExtension())


class K8SLinkProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        el = etree.Element("a")
        el.text = "More info"
        el.set("href", m.group(1))
        return el, m.start(0), m.end(0)


class K8SLinkExtension(Extension):
    def extendMarkdown(self, md):
        PATTERN = r'More\s+info:\s+(http\S+)'
        mp = K8SLinkProcessor(PATTERN, md)
        md.inlinePatterns.register(mp, 'k8s-link', 200)
        md.registeredExtensions.append(K8SLinkExtension())
