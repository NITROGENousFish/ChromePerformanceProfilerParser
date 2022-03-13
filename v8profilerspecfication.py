import json
import os
import sys
from enum import Enum
import datetime

class Phases(Enum):
    Duration_Begin = "B"
    Duration_End = "E"
    Complete = "X"
    Instant = "I"
    Instant_Deprecated = "i"
    Counter = "C"
    Async_Nestable_Start = "b"
    Async_Nestable_Instant = "n"
    Async_Nestable_End = "e"
    Flow_Start = "s"
    Flow_Step = "t"
    Flow_end = "f"
    Sample = "P"
    Object_Created = "N"
    Object_Snapshot = "O"
    Object_Destroyed = "D"
    Metadata = "M"
    MemoryDump_Global = "V"
    MemoryDump_Process = "v"
    Mark = "R"
    ClockSync = "c"
    Context_Enter = "("
    Context_Leave = ")"
    LinkingID = "="

MicrosecondsType = int

def _judge_type_and_return(right,hintstr,typeobj,allowNone=True):
    if right == None:
        if allowNone==True:
            return right
        else:
            
            raise ValueError(f"{hintstr} cannot be None")
    else:
        if type(right) == typeobj:
            return right
        else:
            
            raise TypeError(f"{hintstr} is not {typeobj} type")
class MetaEvents(object):
    def __init__(self,name=None,cat=None,ph:Phases=None,ts=None,pid=None,tid=None,args=None,tts=None,cname=None):
        """ts && tts API文档有问题, 默认传入int, 单位µs
            tts 和 cname 是可选字段
        """
        self.name = _judge_type_and_return(name,"name",str)
        self.cat = _judge_type_and_return(cat,"cat",str)
        self.ph = _judge_type_and_return(ph,"ph",Phases)
        self.ts = _judge_type_and_return(ts,"ts",MicrosecondsType)
        self.pid = _judge_type_and_return(pid,"pid",int)
        self.tid = _judge_type_and_return(tid,"tid",int)
        self.args = _judge_type_and_return(args,"args",dict)
        self.tts = _judge_type_and_return(tts,"tts",MicrosecondsType,allowNone=True)
        self.cname = _judge_type_and_return(cname,"cname",MicrosecondsType,allowNone=True)

    def __str__(self):
        return f"BasicInfo: name:{self.name},cat:{self.cat},ph:{self.ph},ts:{self.ts},pid:{self.pid},tid:{self.tid},tts:{self.tts},args:{self.args}"
class DurationEvents(MetaEvents):
    """分为开始和结束两个状态，两行
    Duration events provide a way to mark a duration of work on a given thread
    B(egin) Events must come before correspoding E(nd) event
    ** If you provide args to both the B and E events then the arguments will be merged.
    ** If there is a duplicate argument value provided the E event argument will be taken and the B event argument will be discarded.
    """
    def __init__(self,pid,tid,ph,ts,**kw):
        assert ph==Phases["Duration_Begin"] or ph==Phases["Duration_End"]
        super(DurationEvents,self).__init__(pid=pid,tid=tid,ph=ph,ts=ts,**kw)
    
class CompleteEvents(MetaEvents):
    """相比上面缩成一行，有开始和持续时间
    Each complete event logically combines a pair of duration (B and E) events.
    """
    def __init__(self,pid,tid,ph,ts,dur,tdur=None,**kw):
        assert ph==Phases["Complete"]
        super(CompleteEvents,self).__init__(pid=pid,tid=tid,ph=ph,ts=ts,**kw)
        self.dur = _judge_type_and_return(dur,"dur",MicrosecondsType)
        self.tdur = _judge_type_and_return(tdur,"tdur",MicrosecondsType,allowNone=True)

class InstantEvents(MetaEvents):
    """马上发生，没有延迟事件
    The instant events correspond to something that happens but has no duration associated with it
    
    value of s(cope)
        t(hread):  A thread scoped event will draw the height of a single thread. 
        p(rocess): A process scoped event will draw through all threads of a given process.
        g(lobal):  A global scoped event will draw a time from the top to the bottom of the timeline.

    """
    def __init__(self,pid,tid,ph,ts,s='t',**kw):
        assert ph==Phases["Instant"]
        super(InstantEvents,self).__init__(pid=pid,tid=tid,ph=ph,ts=ts,**kw)
        assert s in ['g','p','t']
        self.s = _judge_type_and_return(s,"s",str)
        
class CounterEvents(MetaEvents):
    """计数器事件，暂时还没有遇到，raise未实现exception
    The counter events can track a value or multiple values as they change over time
    Each counter can be provided with multiple series of data to display. 
    """
    def __init__(self,ph,id=None,**kw):
        assert ph==Phases["Counter"]
        super(CounterEvents,self).__init__(ph=ph,**kw)
        self.id = _judge_type_and_return(id,"id",str)
        if self.id is not None:
            self.counter_name = self.id+"_"+self.name+"_"+self.pid
        else:
            self.counter_name = self.name+"_"+self.pid
        raise NotImplementedError("CounterEvents (ph=\"C\") not implemented")
        
class AsyncEvents(MetaEvents):
    """用于明确异步事件
    We consider the events with the same category and id as events from the same event tree. 
    
    有关id2：
        异步事件默认是global的 ObjectEvents是Process local的；引入id2代替id显示指出是process-local还是global的
    """
    def __init__(self,ph,id=None,scope=None,id2=None,**kw):
        assert ph==Phases["Async_Nestable_Start"] or ph==Phases["Async_Nestable_Instant"] or ph==Phases["Async_Nestable_End"]
        super(AsyncEvents,self).__init__(ph=ph,**kw)
        self.id = _judge_type_and_return(id,"id",str)
        self.scope = _judge_type_and_return(scope,"scope",str,allowNone=True)
        self.id2 = _judge_type_and_return(id2,"id2",dict,allowNone=True)
        self.id2_process_state=None
        if self.id2 != None:
            if "local" in self.id2.keys():
                self.id2_process_state = "local"
            if "global" in self.id2.keys():
                self.id2_process_state = "global"
            if self.id != None:
                raise NotImplementedError("not implemented when both id && id2 exist")
            else:
                self.id = _judge_type_and_return(self.id2[self.id2_process_state],"id2_parsed",str)
    def __str__(self):
        superreturn = super(AsyncEvents,self).__str__()
        return f"{superreturn}\nuse id2:{self.id2_process_state}, id:{self.id}, scope:{self.scope}"
class FlowEvents(MetaEvents):
    """flow事件和Async事件差不多，但是允许持续时间关联到跨thread/process的其他内容，箭头事件
    Visually, think of a flow event as an arrow between two duration events.
    flow events must bind to specific slices in order to exist. 
        enclosing slice binding, meaning the flow event is bound to its enclosing slice
        next slice binding, meaning the flow event is bound to the next slice that happens in time
    
    增加了id字段，类型是int
    12677 {'args': {}, 'cat': 'loading', 'id': 0, 'name': 'WebURLLoader::Context::Start', 'ph': <Phases.Flow_Start: 's'>, 'pid': 88331, 'tid': 259, 'ts': 1420058437625}
    """
    def __init__(self,ph,id=None,scope=None,bp=None,**kw):
        assert ph==Phases["Flow_Start"] or ph==Phases["Flow_Step"] or ph==Phases["Flow_end"]
        super(FlowEvents,self).__init__(ph=ph,**kw)
        self.bp = _judge_type_and_return(bp,"bp",str,allowNone=True)
        self.id = _judge_type_and_return(id,"id",int)  #! 只有这里的id是int
        self.scope = _judge_type_and_return(scope,"scope",str,allowNone=True)
class SampleEvents(MetaEvents):
    """ adding sampling-profiler based results in a trace
    """
    def __init__(self,ph,id=None,**kw):
        assert ph==Phases["Sample"]
        super(SampleEvents,self).__init__(ph=ph,**kw)
        self.id = _judge_type_and_return(id,"id",str)  #! 只有这里的id是int
        
        
class ObjectEvents(MetaEvents):
    """标记一个对象的存活情况的，包含创建和销毁时间（不含邮args字段）
    快照相当于中间的一个print，会把变量的详细信息写到args里面
    Objects are a building block to track complex data structures in traces.
    id: pointer str,(eg.: "0x1000")
    """
    def __init__(self,ph,id=None,scope=None,id2=None,**kw):
        assert ph==Phases["Object_Created"] or ph==Phases["Object_Snapshot"] or ph==Phases["Object_Destroyed"]
        super(ObjectEvents,self).__init__(ph=ph,**kw) 
        self.id = _judge_type_and_return(id,"id",str)
        self.scope = _judge_type_and_return(scope,"scope",str,allowNone=True)
        self.id2 = _judge_type_and_return(id2,"id2",dict,allowNone=True)
        self.id2_process_state=None
        if self.id2 != None:
            if "local" in self.id2.keys():
                self.id2_process_state = "local"
            if "global" in self.id2.keys():
                self.id2_process_state = "global"
            if self.id != None:
                raise NotImplementedError("not implemented when both id && id2 exist")
            else:
                self.id = _judge_type_and_return(self.id2[self.id2_process_state],"id2_parsed",str)
        
        if "snapshot" in self.args.keys() and type(self.args["snapshot"]) == dict and "cat" in self.args["snapshot"].keys():
            raise NotImplementedError("Snapshot type override not implemented")
         
class MetadataEvents(MetaEvents):
    """提供额外信息
    """
    # 五种提供信息的额外存储位置
    metadata_items_dict = { 
        "process_name":"name",
        "process_labels":"labels",
        "process_sort_index":"sort_index",
        "thread_name":"name",
        "thread_sort_index":"sort_index",
        "process_uptime_seconds":"uptime",
        "num_cpus":"number"
    }
    def __init__(self,ph,**kw):
        assert ph==Phases["Metadata"]
        super(MetadataEvents,self).__init__(ph=ph,**kw)
        self.metadata_item = self.args[MetadataEvents.metadata_items_dict[self.name]]

        
class MemoryDumpEvents(MetaEvents):
    def __init__(self,ph,**kw):
        assert ph==Phases["MemoryDump_Global"] or ph==Phases["MemoryDump_Process"]
        super(MemoryDumpEvents,self).__init__(ph=ph,**kw) 
        raise NotImplementedError("MemoryDumpEvents not implemented")
class MarkEvents(MetaEvents):
    def __init__(self,pid,tid,ph,ts,s=None,**kw):
        assert ph==Phases["Mark"]
        super(MarkEvents,self).__init__(pid=pid,tid=tid,ph=ph,ts=ts,**kw)
        assert s in ['g','p','t']
        self.s = _judge_type_and_return(s,"s",str,allowNone=True)  #? 不确定这里行不行

class ClockSyncEvents(MetaEvents):
    """ 用于同步时钟，合并多个tracing agents的结果
    Trace Viewer can handle multiple trace logs produced by different tracing agents and synchronize their clock domains.
    """
    def __init__(self,ph,**kw):
        assert ph==Phases["ClockSync"]
        super(ClockSyncEvents,self).__init__(ph=ph,**kw) 
        raise NotImplementedError("ClockSyncEvents not implemented")
        
class ContextEvents(MetaEvents):
    def __init__(self,ph,**kw):
        assert ph==Phases["Context_Enter"] or ph==Phases["Context_Leave"]
        super(ContextEvents,self).__init__(ph=ph,**kw) 
        raise NotImplementedError("ContextEvents not implemented")

class LinkingIDEvents(MetaEvents):
    """ 用于标记两个id是相等的
    Events with phase "=" can be used to specify that two ids are identical.
    """
    def __init__(self,ph,**kw):
        assert ph==Phases["LinkingID"]
        super(LinkingIDEvents,self).__init__(ph=ph,**kw)
        self.second_id = self.args["linked_id"]
        raise NotImplementedError("LinkingIDEvents not implemented")


def phasesToEvents(ph_char:str):
    if Phases(ph_char) == Phases["Duration_Begin"]:
        return DurationEvents
    if Phases(ph_char) == Phases["Duration_End"]:
        return DurationEvents
    if Phases(ph_char) == Phases["Complete"]:
        return CompleteEvents
    if Phases(ph_char) == Phases["Instant"]:
        return InstantEvents
    if Phases(ph_char) == Phases["Instant_Deprecated"]:
        return InstantEvents
    if Phases(ph_char) == Phases["Counter"]:
        return CounterEvents
    if Phases(ph_char) == Phases["Async_Nestable_Start"]:
        return AsyncEvents
    if Phases(ph_char) == Phases["Async_Nestable_Instant"]:
        return AsyncEvents
    if Phases(ph_char) == Phases["Async_Nestable_End"]:
        return AsyncEvents
    if Phases(ph_char) == Phases["Flow_Start"]:
        return FlowEvents
    if Phases(ph_char) == Phases["Flow_Step"]:
        return FlowEvents
    if Phases(ph_char) == Phases["Flow_end"]:
        return FlowEvents
    if Phases(ph_char) == Phases["Sample"]:
        return SampleEvents
    if Phases(ph_char) == Phases["Object_Created"]:
        return ObjectEvents
    if Phases(ph_char) == Phases["Object_Snapshot"]:
        return ObjectEvents
    if Phases(ph_char) == Phases["Object_Destroyed"]:
        return ObjectEvents
    if Phases(ph_char) == Phases["Metadata"]:
        return MetadataEvents
    if Phases(ph_char) == Phases["MemoryDump_Global"]:
        return MemoryDumpEvents
    if Phases(ph_char) == Phases["MemoryDump_Process"]:
        return MemoryDumpEvents
    if Phases(ph_char) == Phases["Mark"]:
        return MarkEvents
    if Phases(ph_char) == Phases["ClockSync"]:
        return ClockSyncEvents
    if Phases(ph_char) == Phases["Context_Enter"]:
        return ContextEvents
    if Phases(ph_char) == Phases["Context_Leave"]:
        return ContextEvents
    if Phases(ph_char) == Phases["LinkingID"]:
        return LinkingIDEvents

"""
profile_file = json.load(open("./Profile-20220227T164144.json"))
parsedlist = []
for idx,line in enumerate(profile_file):
    line["ph"] = v8p.Phases(line["ph"])
    parsedcontent = v8p.phasesToEvents(line["ph"])(**line)
    parsedlist.append(parsedcontent)
"""

if __name__ == "__main__":
    profile_file = json.load(open("./Profile-20220227T164144.json"))
    parsedlist = []
    for idx,line in enumerate(profile_file):
        try:
            line["ph"] = Phases(line["ph"])
            parsedcontent = phasesToEvents(line["ph"])(**line)
        except:
            print(idx,line)
            parsedcontent = phasesToEvents(line["ph"])(**line)
        parsedlist.append(parsedcontent)
