from markdown.inlinepatterns import InlineProcessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree


class ModelLinkProcessor(InlineProcessor):
    def handleMatch(self, m, data):
        module, classe = m.group(1), m.group(2)
        code = etree.Element("code")
        el = etree.Element("a")
        el.text = (module or "") + classe

        if module:
            parts = module[:-1].split(".")
            href = f"{'../'*len(parts)}{'/'.join(parts)}/index.html#{classe.lower()}"
        else:
            href = f"#{classe.lower()}"

        el.set("href", href)
        code.append(el)
        return code, m.start(0), m.end(0)


class ModelLinkExtension(Extension):
    def extendMarkdown(self, md):
        PATTERN = r'``(?:List\[)?([a-z_0-9.]+)?([A-Z][a-z_0-9A-Z]+)\]?``'
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
