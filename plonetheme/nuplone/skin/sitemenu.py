import collections
from Acquisition import aq_inner
from Acquisition import aq_parent
from zope.interface import Interface
from five import grok
from plonetheme.nuplone.skin.interfaces import NuPloneSkin
from plonetheme.nuplone.utils import checkPermission
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.ActionInformation import ActionInfo
from OFS.interfaces import ICopyContainer
from OFS.interfaces import ICopySource


grok.templatedir("templates")

FactoryInfo = collections.namedtuple("FactoryInfo", "id title description url")

class Sitemenu(grok.View):
    grok.context(Interface)
    grok.name("sitemenu")
    grok.layer(NuPloneSkin)
    grok.template("sitemenu")

    def update(self):
        self.view_type=self.request.get("view_type", "view")

        context=aq_inner(self.context)
        is_root=ISiteRoot.providedBy(context)
        is_copyable=not is_root and ICopySource.providedBy(context)
        self.can_copy=is_copyable and context.cb_isCopyable()
        self.can_cut=is_copyable and context.cb_isMoveable()
        self.can_paste=ICopyContainer.providedBy(context) and context.cb_dataValid()
        if not is_root:
            parent=aq_parent(context)
            self.can_delete=checkPermission(parent, "Delete objects")
        else:
            self.can_delete=False


    def factories(self):
        context=aq_inner(self.context)
        ftis=context.allowedContentTypes()
        if not ftis:
            return []

        tt=getToolByName(context, "portal_types")
        ec=tt._getExprContext(context)
        actions=[ActionInfo(fti, ec) for fti in ftis]
        actions=[FactoryInfo(action.get("id"),
                             action.get("title") or action.get("id"), 
                             action.get("description") or None,
                             action["url"])
                 for action in actions]
        actions.sort(key=lambda x: x.title)
        return actions
