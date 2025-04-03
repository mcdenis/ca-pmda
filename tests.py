import unittest
import ca_pmda
import copy
import xml.etree.ElementTree


sample_item = xml.etree.ElementTree.fromstring("""
<CommunicationProfile version="1.0.0">
    <ID>1234567</ID>
    <UseForWrite>false</UseForWrite>
    <Rank>2</Rank>
    <ProfileName>MyProfile1</ProfileName>
    <IsAlso>
        <IsA name="SNMPv3Profile" rootURL="profiles/snmpv3" />
    </IsAlso>
    <CommunicationFailurePolicy version="1.0.0">
        <Retries>3</Retries>
        <Timeout>2000</Timeout>
    </CommunicationFailurePolicy>
</CommunicationProfile>
""")


# TODO unused for now.
sample_list = xml.etree.ElementTree.fromstring("""
<CommunicationProfileList>
    <CommunicationProfile version="1.0.0">
        <ID>1234567</ID>
        <UseForWrite>false</UseForWrite>
        <Rank>2</Rank>
        <ProfileName>MyProfile1</ProfileName>
        <IsAlso>
            <IsA name="SNMPv3Profile" rootURL="profiles/snmpv3" />
        </IsAlso>
        <CommunicationFailurePolicy version="1.0.0">
            <Retries>3</Retries>
            <Timeout>2000</Timeout>
        </CommunicationFailurePolicy>
    </CommunicationProfile>
    <CommunicationProfile version="1.0.0">
        <ID>2345</ID>
        <UseForWrite>false</UseForWrite>
        <Rank>8</Rank>
        <ProfileName>MyProfile2</ProfileName>
        <IsAlso>
            <IsA name="SNMPv3Profile" rootURL="profiles/snmpv3" />
        </IsAlso>
        <CommunicationFailurePolicy version="1.0.0">
            <Retries>3</Retries>
            <Timeout>2000</Timeout>
        </CommunicationFailurePolicy>
    </CommunicationProfile>
    <CommunicationProfile version="1.0.0">
        <ID>2345678</ID>
        <UseForWrite>false</UseForWrite>
        <Rank>1</Rank>
        <ProfileName>MyProfile3</ProfileName>
        <IsAlso>
            <IsA name="SNMPv3Profile" rootURL="profiles/snmpv3" />
        </IsAlso>
        <CommunicationFailurePolicy version="1.0.0">
            <Retries>3</Retries>
            <Timeout>2000</Timeout>
        </CommunicationFailurePolicy>
    </CommunicationProfile>
    <CommunicationProfile version="1.0.0">
        <ID>3456789</ID>
        <UseForWrite>false</UseForWrite>
        <Rank>3</Rank>
        <ProfileName>MyProfile4</ProfileName>
        <IsAlso>
            <IsA name="SNMPv3Profile" rootURL="profiles/snmpv3" />
        </IsAlso>
        <CommunicationFailurePolicy version="1.0.0">
            <Retries>3</Retries>
            <Timeout>2000</Timeout>
        </CommunicationFailurePolicy>
    </CommunicationProfile>
</CommunicationProfileList>
""")


def str_equal_whitespace(str1: str | None, str2: str | None) -> bool:
    return (str1 or "").strip() == (str2 or "").strip()


def elements_equal(e1: xml.etree.ElementTree.Element,
                   e2: xml.etree.ElementTree.Element) -> bool:
    """
    Adapted from https://stackoverflow.com/a/24349916
    """
    
    if e1.tag != e2.tag: return False
    if not str_equal_whitespace(e1.text, e2.text): return False
    if not str_equal_whitespace(e1.tail, e2.tail): return False
    if e1.attrib != e2.attrib: return False
    if len(e1) != len(e2): return False
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))


def assertElementsEqual(test_case: unittest.TestCase,
                        e1: xml.etree.ElementTree.Element,
                        e2: xml.etree.ElementTree.Element) -> None:
    return test_case.assertTrue(elements_equal(e1, e2), "XML elements are not equal.")


class TestDynamicModel(unittest.TestCase):

    def testPropRead(self) -> None:
        doc = sample_item
        model = ca_pmda.DynamicModel(doc)
        
        # Get reference elements.
        id_element = doc.find("ID")
        use_for_write_element = doc.find("UseForWrite")
        communication_failure_policy_element = doc.find("CommunicationFailurePolicy")
        assert id_element is not None
        assert use_for_write_element is not None
        assert communication_failure_policy_element is not None

        self.assertEqual(model.ID, id_element.text)
        self.assertEqual(model.UseForWrite, use_for_write_element.text)
        assertElementsEqual(self,
                            model.CommunicationFailurePolicy.__document__,
                            communication_failure_policy_element)
        

    def testPropDelete(self) -> None:
        # Create and manipulate model.
        model = ca_pmda.DynamicModel(copy.deepcopy(sample_item))
        del model.UseForWrite
        del model.CommunicationFailurePolicy

        # Create expected doc.
        expected_doc = copy.deepcopy(sample_item)
        elements_to_remove = (
            expected_doc.find("UseForWrite"),
            expected_doc.find("CommunicationFailurePolicy")
        )
        for e in elements_to_remove:
            assert e is not None
            expected_doc.remove(e)
        
        # Assertion
        assertElementsEqual(self, model.__document__, expected_doc)
        

    def testCustomWithScalar(self) -> None:
        model = ca_pmda.dynamic_model("ManageableDevice",
                                      version="1.0.0",
                                      SNMPProfileID=4567,
                                      SNMPProfileVersion="SNMPV3")
        
        expected_doc = xml.etree.ElementTree.fromstring("""
            <ManageableDevice version="1.0.0">
                <SNMPProfileID>4567</SNMPProfileID>
                <SNMPProfileVersion>SNMPV3</SNMPProfileVersion>
            </ManageableDevice>
            """)
        assertElementsEqual(self, model.__document__, expected_doc)
        

    def testCustomWithScalarAndComplex(self) -> None:
        child_model = ca_pmda.dynamic_model("DataCollectionMgrId",
                                            version="1.0.0",
                                            PrevMDRItemID="1234")
        parent_model = ca_pmda.dynamic_model("ManageableDevice",
                                             version="1.0.0",
                                             Model="Cisco ISR4479",
                                             DataCollectionMgrId=child_model)
        expected_doc = xml.etree.ElementTree.fromstring("""
            <ManageableDevice version="1.0.0">
                <Model>Cisco ISR4479</Model>
                <DataCollectionMgrId version="1.0.0">
                    <PrevMDRItemID>1234</PrevMDRItemID>
                </DataCollectionMgrId>
            </ManageableDevice>
            """)
        assertElementsEqual(self, parent_model.__document__, expected_doc)
        

class TestExpression(unittest.TestCase):
    def testAttributeComparison(self) -> None:
        expr = ca_pmda.AttributeComparison("DataCollectionMgrId.PrevMDRItemID", "EQUAL", 1234)
        expr_doc = expr.__toxml__()
        expected_doc = xml.etree.ElementTree.fromstring("""
            <DataCollectionMgrId.PrevMDRItemID type="EQUAL">1234</DataCollectionMgrId.PrevMDRItemID>
            """)
        assertElementsEqual(self, expr_doc, expected_doc)


    def testComplex(self) -> None:
        AttributeComparison = ca_pmda.AttributeComparison
        Not = ca_pmda.Not
        And = ca_pmda.And
        Or = ca_pmda.Or
        
        expr = Not(Or(AttributeComparison("ManageableDevice.Model", "CONTAINS", "ISR4479"),
                      AttributeComparison("DataCollectionMgrId.PrevMDRItemID", "LESS_OR_EQUAL", 789),
                      And(AttributeComparison("Lifecycle.State", "EQUAL", "RETIRED"),
                          AttributeComparison("ManageableDevice.SystemName", "ENDS_WITH", ".my-org.com"))))
        expr_doc = expr.__toxml__()
        expected_doc = xml.etree.ElementTree.fromstring("""
            <Not>
                <Or>
                    <ManageableDevice.Model type="CONTAINS">ISR4479</ManageableDevice.Model>
                    <DataCollectionMgrId.PrevMDRItemID type="LESS_OR_EQUAL">789</DataCollectionMgrId.PrevMDRItemID>
                    <And>
                        <Lifecycle.State type="EQUAL">RETIRED</Lifecycle.State>
                        <ManageableDevice.SystemName type="ENDS_WITH">.my-org.com</ManageableDevice.SystemName>
                    </And>
                </Or>                                      
            </Not>
            """)
        assertElementsEqual(self, expr_doc, expected_doc)