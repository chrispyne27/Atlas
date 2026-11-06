export const symbols = [
 ['frame','RenderEngine::renderFrame','src/render/RenderEngine.cpp',84,'render','Compose and submit one frame within the frame budget.','void RenderEngine::renderFrame(const FrameContext& ctx) {\n  const SceneSnapshot scene = sceneGraph.update(ctx.delta);\n  const DrawList visible = culler.cull(scene, ctx.camera);\n  uiLayer.compose(ctx.viewport);\n  commandQueue.submit(visible);\n  frameMetrics.record(ctx.clock.elapsed());\n}',{owner:'Rendering team',criticality:'High',budget:'16.7 ms / frame',hazard:'HZ-004 · stale frame',design:'ADR-012 · deterministic frame loop'}],
 ['scene','SceneGraph::update','src/scene/SceneGraph.cpp',42,'render','Update transforms and produce an immutable scene snapshot.','SceneSnapshot SceneGraph::update(float dt) {\n  transforms.updateWorld(dt);\n  return snapshot(nodes);\n}'],
 ['transforms','TransformSystem::updateWorld','src/scene/TransformSystem.cpp',66,'render','Recalculate dirty world transforms in parent order.','void TransformSystem::updateWorld(float dt) {\n  for (NodeId id : dirtyNodes) {\n    world[id] = parentWorld(id) * local[id];\n  }\n}'],
 ['cull','FrustumCuller::cull','src/render/FrustumCuller.cpp',35,'render','Reject objects outside the view frustum.','DrawList FrustumCuller::cull(const SceneSnapshot& scene,\n                            const Camera& camera) {\n  return filterVisible(scene, camera.frustum());\n}'],
 ['submit','CommandQueue::submit','src/render/CommandQueue.cpp',103,'render','Submit a stable, bounded draw list to the graphics backend.','void CommandQueue::submit(const DrawList& list) {\n  for (const DrawCall& draw : list) {\n    shaderCache.bind(draw.material);\n    backend.draw(draw);\n  }\n}'],
 ['shader','ShaderCache::bind','src/render/ShaderCache.cpp',57,'render','Reuse compiled shader programs by material key.','void ShaderCache::bind(MaterialId material) {\n  const Program& program = cache.lookup(material);\n  backend.useProgram(program.id);\n}'],
 ['metrics','FrameMetrics::record','src/telemetry/FrameMetrics.cpp',29,'core','Store frame duration in a bounded metrics ring.','void FrameMetrics::record(Duration elapsed) {\n  durations.push(elapsed.milliseconds());\n  if (elapsed > frameBudget) logger.warn("frame budget");\n}'],
 ['ui','UILayer::compose','src/ui/UILayer.cpp',71,'ui','Build the UI draw list from the active widget tree.','void UILayer::compose(const Viewport& view) {\n  layout.resolve(root, view);\n  for (Widget& widget : visibleWidgets) {\n    widget.draw(uiCommands);\n  }\n}',{owner:'Experience team',criticality:'Medium',design:'ADR-008 · retained UI tree'}],
 ['layout','LayoutEngine::resolve','src/ui/LayoutEngine.cpp',48,'ui','Resolve widget bounds against the viewport.','void LayoutEngine::resolve(Widget& root, Viewport view) {\n  root.setBounds(view.bounds());\n  resolveChildren(root);\n}'],
 ['widget','Widget::draw','src/ui/Widget.cpp',90,'ui','Append a widget’s visual primitives to a command buffer.','void Widget::draw(UICommandBuffer& commands) {\n  commands.rect(bounds, style.background);\n  textRenderer.draw(label, bounds.origin());\n}'],
 ['text','TextRenderer::draw','src/ui/TextRenderer.cpp',63,'ui','Render text from a cached glyph atlas.','void TextRenderer::draw(StringView text, Point origin) {\n  const Atlas& atlas = resources.get(fontAtlasId);\n  emitGlyphs(text, atlas, origin);\n}'],
 ['input','InputRouter::dispatch','src/input/InputRouter.cpp',38,'ui','Route each input event to the focused widget.','void InputRouter::dispatch(const InputEvent& event) {\n  WidgetId target = hitTest(event.position);\n  eventBus.publish(UIEvent(target, event));\n}'],
 ['hit','HitTester::hitTest','src/input/HitTester.cpp',27,'ui','Find the topmost interactive widget at a position.','WidgetId HitTester::hitTest(Point point) {\n  return widgetTree.topmostAt(point);\n}'],
 ['event','EventBus::publish','src/core/EventBus.cpp',52,'core','Dispatch typed events to registered subscribers.','void EventBus::publish(const Event& event) {\n  for (Subscriber& s : subscribers[event.type]) {\n    s.onEvent(event);\n  }\n}',{criticality:'High',constraint:'Single-threaded dispatch',design:'ADR-005 · explicit event routing'}],
 ['resource','ResourceCache::get','src/resources/ResourceCache.cpp',77,'resources','Return a cached resource or the deterministic fallback.','Resource& ResourceCache::get(ResourceId id) {\n  Resource* found = cache.find(id);\n  return found ? *found : fallback;\n}',{owner:'Platform team',criticality:'High',hazard:'HZ-009 · missing asset'}],
 ['load','AssetLoader::load','src/resources/AssetLoader.cpp',44,'resources','Decode a local asset and publish its availability.','Result AssetLoader::load(const Path& path) {\n  const Bytes data = fileSystem.read(path);\n  cache.insert(decode(data));\n  eventBus.publish(AssetReady(path));\n  return Result::ok();\n}'],
 ['file','FileSystem::read','src/platform/FileSystem.cpp',31,'core','Read an asset file through the platform abstraction.','Bytes FileSystem::read(const Path& path) {\n  return platform.readFile(path);\n}'],
 ['logger','Logger::warn','src/core/Logger.cpp',25,'core','Append a bounded diagnostic entry.','void Logger::warn(StringView message) {\n  entries.push(LogLevel::Warning, message);\n}'],
 ['resize','RenderEngine::resize','src/render/RenderEngine.cpp',121,'render','Update viewport dimensions and invalidate UI layout.','void RenderEngine::resize(Size size) {\n  viewport.resize(size);\n  uiLayer.compose(viewport);\n  eventBus.publish(ViewportChanged(size));\n}'],
 ['shutdown','RenderEngine::shutdown','src/render/RenderEngine.cpp',142,'render','Release resources in reverse dependency order.','void RenderEngine::shutdown() {\n  commandQueue.flush();\n  resourceCache.releaseAll();\n}']
].map(([id,name,path,line,component,description,code,metadata={}])=>({id,name,path,line,component,description,code,kind:'method',metadata:{owner:'Platform team',criticality:'Medium',language:'C++',baseline:'DEMO-1.4',...metadata}}));
export const requirements = [
 ['REQ-REN-001','Maintain a 60 Hz frame loop','The renderer shall compose and submit a frame within 16.7 ms under the nominal reference scene.','render','High','Frame timing analysis',['frame','cull','submit'],'test-frame','SYS-001','Timing','HZ-004'],
 ['REQ-UI-002','Resolve responsive widget layouts','The UI shall recompute visible widget bounds after a viewport size change.','ui','Medium','Viewport resize test',['ui','layout','resize'],'test-layout','SYS-002','Functional','—'],
 ['REQ-RES-003','Provide a missing-asset fallback','The resource cache shall return a deterministic fallback when a requested asset is unavailable.','resources','High','Missing resource test',['resource'],'test-resource','SYS-003','Robustness','HZ-009'],
 ['REQ-INP-004','Dispatch input deterministically','Input events shall be delivered to the focused widget in arrival order.','ui','High','Ordered input test',['input','event'],'test-input','SYS-002','Functional','—'],
 ['REQ-OBS-005','Record frame budget overruns','The engine shall record a diagnostic when a frame exceeds its configured budget.','core','Medium','Diagnostic inspection',['metrics','logger'],null,'SYS-001','Observability','HZ-004'],
 ['REQ-TXT-006','Render cached glyphs','Text rendering shall reuse glyph atlas resources across frames.','ui','Low','Cache reuse test',['text','resource'],null,'SYS-002','Performance','—'],
 ['REQ-LIF-007','Release resources in order','Shutdown shall release graphics resources in reverse dependency order.','render','Medium','Lifecycle test',['shutdown'],null,'SYS-003','Lifecycle','—'],
 ['REQ-ISO-008','Isolate graphics backend access','Graphics API calls shall be confined to the platform backend boundary.','core','High','Dependency rule analysis',[],null,'SYS-003','Architecture','—']
].map(([id,name,description,component,criticality,verification,methods,test,parent,category,hazard])=>({id,name,description,kind:'requirement',component,methods,test,parent,category,metadata:{owner:component==='ui'?'Experience team':component==='render'?'Rendering team':'Platform team',criticality,verification,parent,category,hazard,baseline:'DEMO-1.4',provenance:'Synthetic specification §4',confidence:'Explicit sample link'},status:!methods.length?'Unlinked':test?'Covered':'Partial'}));
export const tests = [
 ['test-frame','FrameBudget.NominalScene','tests/render/FrameBudgetTest.cpp',18,'frame'],
 ['test-layout','Layout.ResizeViewport','tests/ui/LayoutTest.cpp',22,'layout'],
 ['test-resource','ResourceCache.MissingAsset','tests/resources/ResourceCacheTest.cpp',14,'resource'],
 ['test-input','InputRouter.ArrivalOrder','tests/input/InputRouterTest.cpp',30,'input']
].map(([id,name,path,line,target])=>({id,name,path,line,target,kind:'test',component:symbols.find(s=>s.id===target).component,description:'Illustrative test fixture; linked evidence only. No real test execution is claimed.',code:`TEST(${name.replace('.', ', ')}) {\n  // Synthetic fixture: arrange a deterministic scenario.\n  const auto result = fixture.runScenario();\n  EXPECT_TRUE(result.matchesExpected());\n}`,metadata:{owner:'Quality engineering',result:'Synthetic pass',baseline:'DEMO-1.4',provenance:'Demo fixture'}}));
export const components = ['render','ui','resources','core'].map(id=>({id:'component-'+id,name:{render:'Rendering',ui:'User interface',resources:'Resources',core:'Core & platform'}[id],kind:'component',component:id,description:'A synthetic component boundary for exploring architectural dependencies.',metadata:{owner:id==='render'?'Rendering team':id==='ui'?'Experience team':'Platform team',baseline:'DEMO-1.4'}}));
const calls = [['frame','scene'],['frame','cull'],['frame','ui'],['frame','submit'],['frame','metrics'],['scene','transforms'],['submit','shader'],['ui','layout'],['ui','widget'],['widget','text'],['text','resource'],['input','hit'],['input','event'],['metrics','logger'],['load','file'],['load','event'],['resize','ui'],['resize','event']];
export const edges = [
 ...calls.map(([from,to])=>({from,to,type:'calls'})),
 ...symbols.map(s=>({from:s.id,to:'component-'+s.component,type:'belongs to'})),
 ...[['render','ui'],['render','resources'],['render','core'],['ui','resources'],['ui','core'],['resources','core']].map(([a,b])=>({from:'component-'+a,to:'component-'+b,type:'depends on'})),
 ...requirements.flatMap(r=>r.methods.map(id=>({from:id,to:r.id,type:'implements'}))),
 ...requirements.filter(r=>r.test).map(r=>({from:r.test,to:r.id,type:'verifies'})),
 ...tests.map(t=>({from:t.id,to:t.target,type:'exercises'}))
];
export const nodes = [...symbols,...requirements,...tests,...components];
export const byId = Object.fromEntries(nodes.map(n=>[n.id,n]));
export const stages = [
 {id:'parse',name:'Parse & symbols',description:'Syntax trees, definitions, and file locations.',seconds:24,disk:35,ram:180,capability:'Exact symbol search',required:true},
 {id:'graph',name:'Call & dependency graph',description:'Resolve relationships and compute change impact.',seconds:44,disk:65,ram:260,capability:'Relationship traversal'},
 {id:'trace',name:'Requirements & metadata',description:'Join requirement IDs, tests, ownership, and design decisions.',seconds:18,disk:18,ram:60,capability:'Engineering traceability'},
 {id:'vector',name:'Semantic embeddings',description:'Encode chunks for similarity retrieval.',seconds:90,disk:120,ram:220,capability:'Concept-based retrieval'},
 {id:'history',name:'History & summaries',description:'Summarize changes and preserve temporal context.',seconds:140,disk:85,ram:160,capability:'Change context'}
];
export function model({loc=1000000,workers=4,changed=2,fanout=3,enabled=['parse','graph','trace','vector']}) {
 const scale=loc/100000, speed=1+0.65*(workers-1);
 const active=stages.filter(s=>enabled.includes(s.id));
 const work=active.map(s=>({...s,full:s.seconds*scale/speed,affected:Math.min(1,changed/100*(s.id==='graph'?fanout:s.id==='parse'?1:1+(fanout-1)*0.45))}));
 const full=work.reduce((a,s)=>a+s.full,0);
 const incremental=2+work.reduce((a,s)=>a+s.full*s.affected,0);
 const disk=work.reduce((a,s)=>a+s.disk*scale,0);
 const memory=280+Math.max(...active.map(s=>s.ram),0)*workers+scale*15;
 return {work,full,incremental,disk,memory,speed,affected:Math.min(100,changed*fanout)};
}
